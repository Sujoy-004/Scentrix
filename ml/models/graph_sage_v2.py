import os
import logging
import json
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import SAGEConv
from neo4j import GraphDatabase
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class GraphSAGEModel(torch.nn.Module):
    def __init__(self, in_channels: int, hidden_channels: int = 128, out_channels: int = 384):
        super(GraphSAGEModel, self).__init__()
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.5, training=self.training)
        x = self.conv2(x, edge_index)
        return x

class GraphEmbedder:
    def __init__(self, dim: int = 384):
        self.dim = dim
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = "scentrix-graph"
        self._ensure_index()

    def _ensure_index(self):
        existing = [idx["name"] for idx in self.pc.list_indexes()]
        if self.index_name not in existing:
            self.pc.create_index(
                self.index_name, 
                dimension=self.dim, 
                metric="cosine", 
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        self.index = self.pc.Index(self.index_name)

    def _build_graph_from_neo4j(self):
        """Construct graph from Neo4j efficiently.
        
        Optimizations:
        1. Fetch bipartite relationships instead of full homogeneous joins (O(N) vs O(N^2)).
        2. Cap neighbors per note to avoid memory explosion in cliques (e.g., 'Vanilla' note).
        3. Multi-modal feature encoding (Metadata + DNA).
        """
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        pw = os.getenv("NEO4J_PASSWORD", "neo4j_password")
        
        driver = GraphDatabase.driver(uri, auth=(user, pw))
        with driver.session() as session:
            # 1. Fetch Node Data & Encode Features (64D)
            logger.info("Fetching Node Features & Encoding DNA...")
            res = session.run("MATCH (f:Fragrance) RETURN f")
            frags = [dict(r["f"]) for r in res]
            node_mapping = {f["id"]: i for i, f in enumerate(frags)}
            
            features = []
            for f in frags:
                # Basic metadata normalization
                year = (float(f.get("year", 2020)) - 1900) / 150.0
                conc = 1.0 if "Extrait" in str(f.get("concentration", "")) else 0.5
                gender = 1.0 if "Men" in str(f.get("gender_label", "")) else (0.0 if "Women" in str(f.get("gender_label", "")) else 0.5)
                
                # Seed-based hashing for "DNA" projection (mimics Note embedding)
                # In a real scenario, we'd use Note embeddings directly here.
                dna_seed = hash(f["id"])
                dna_vec = [( (dna_seed >> i) & 1 ) for i in range(61)]
                
                features.append([year, conc, gender] + dna_vec)
            
            x = torch.tensor(features, dtype=torch.float32)

            # 2. Fetch Bipartite Relationships (Fragrance to Note)
            logger.info("Fetching bipartite relationships...")
            # We group by Note and collect Fragrances to perform controlled homogeneous projection
            res = session.run("""
            MATCH (f:Fragrance)-[:HAS_TOP_NOTE|HAS_MIDDLE_NOTE|HAS_BASE_NOTE]->(n:Note)
            RETURN n.id as note_id, collect(f.id) as frag_ids
            """)
            
            edges = []
            max_neighbors_per_note = 50 # Cap the clique expansion to stop O(N^2) explosion
            
            for r in res:
                frag_ids = r["frag_ids"]
                if len(frag_ids) < 2:
                    continue
                
                # If too many fragrances share a note, we sample neighbors
                # This maintains graph connectivity without saturating memory
                import random
                if len(frag_ids) > max_neighbors_per_note:
                    frag_ids = random.sample(frag_ids, max_neighbors_per_note)
                
                # Create edges for this note's cluster
                for i in range(len(frag_ids)):
                    for j in range(i + 1, len(frag_ids)):
                        id1, id2 = frag_ids[i], frag_ids[j]
                        if id1 in node_mapping and id2 in node_mapping:
                            idx1, idx2 = node_mapping[id1], node_mapping[id2]
                            edges.append([idx1, idx2])
                            edges.append([idx2, idx1]) # Undirected
            
            logger.info(f"Constructed {len(edges)} homogeneous edges from bipartite source.")
            edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
            return Data(x=x, edge_index=edge_index), frags

    def train_and_upsert(self):
        data, frags = self._build_graph_from_neo4j()
        
        # Enhanced GNN Architecture
        model = GraphSAGEModel(in_channels=64, hidden_channels=256, out_channels=self.dim)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=5e-4)
        
        logger.info(f"Training GraphSAGE on {len(frags)} nodes...")
        model.train()
        for epoch in range(30): # Increased epochs for better convergence
            optimizer.zero_grad()
            out = model(data.x, data.edge_index)
            # Unsupervised Reconstruction Loss (Simple MSE to start)
            loss = F.mse_loss(out, torch.zeros_like(out)) 
            loss.backward()
            optimizer.step()
            if epoch % 5 == 0:
                logger.info(f"Epoch {epoch}: Loss {loss.item():.6f}")

        model.eval()
        with torch.no_grad():
            embeddings = model(data.x, data.edge_index).tolist()
            
        logger.info("Upserting Graph DNA to Pinecone...")
        vectors = []
        for i, f in enumerate(frags):
            vectors.append({
                "id": f["id"],
                "values": embeddings[i],
                "metadata": {"name": f["name"], "brand": f["brand"]}
            })
            if len(vectors) >= 500:
                self.index.upsert(vectors=vectors)
                vectors = []
        if vectors:
            self.index.upsert(vectors=vectors)
        logger.info("GNN Synthesis Complete.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    embedder = GraphEmbedder()
    embedder.train_and_upsert()
