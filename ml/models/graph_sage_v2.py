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
        self.index_name = "scentscape-graph"
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
        """Construct graph from Neo4j to avoid O(N^2) memory explosion in shared-note cliques."""
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        pw = os.getenv("NEO4J_PASSWORD", "neo4j_password")
        
        driver = GraphDatabase.driver(uri, auth=(user, pw))
        with driver.session() as session:
            # 1. Fetch Fragrance Data for Features
            logger.info("Fetching Node Features...")
            res = session.run("MATCH (f:Fragrance) RETURN f")
            frags = [dict(r["f"]) for r in res]
            node_mapping = {f["id"]: i for i, f in enumerate(frags)}
            
            # Simplified feature vector (Year, Concentration, Gender, Notes Count)
            # 128D projection target? No, let's just use 16D raw data to encode.
            features = []
            for f in frags:
                # Basic normalization
                year = (float(f.get("year", 2020)) - 1900) / 150.0
                conc = 1.0 if "Extrait" in str(f.get("concentration", "")) else 0.5
                gender = 1.0 if "Men" in str(f.get("gender_label", "")) else (0.0 if "Women" in str(f.get("gender_label", "")) else 0.5)
                features.append([year, conc, gender] + [0]*13) # Pad to 16
            
            x = torch.tensor(features, dtype=torch.float32)

            # 2. Fetch Relationships for Edges
            logger.info("Fetching edges...")
            res = session.run("""
            MATCH (f1:Fragrance)-[:HAS_NOTE]->(n:Note)<-[:HAS_NOTE]-(f2:Fragrance)
            WITH f1.id as id1, f2.id as id2 LIMIT 500000
            RETURN id1, id2
            """)
            edges = []
            for r in res:
                if r["id1"] in node_mapping and r["id2"] in node_mapping:
                    edges.append([node_mapping[r["id1"]], node_mapping[r["id2"]]])
            
            edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
            return Data(x=x, edge_index=edge_index), frags

    def train_and_upsert(self):
        data, frags = self._build_graph_from_neo4j()
        
        # Super-lightweight training
        model = GraphSAGEModel(in_channels=16, out_channels=self.dim)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        
        logger.info("Training GraphSAGE...")
        model.train()
        for epoch in range(20):
            optimizer.zero_grad()
            out = model(data.x, data.edge_index)
            # Reconstruction loss (dummy for unsupervised)
            loss = F.mse_loss(out, torch.zeros_like(out))
            loss.backward()
            optimizer.step()
            if epoch % 5 == 0:
                logger.info(f"Epoch {epoch}: Loss {loss.item()}")

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
