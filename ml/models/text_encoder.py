import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from pinecone import Pinecone, ServerlessSpec
try:
    from sentence_transformers import SentenceTransformer
except ImportError as exc:
    raise ImportError(
        "Missing optional dependency 'sentence-transformers'. "
        "Install it with 'pip install sentence-transformers' to use ml.models.text_encoder."
    ) from exc

logger = logging.getLogger(__name__)

class TextEncoder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize SentenceTransformer and Pinecone client."""
        logger.info(f"Loading sentence transformer model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        pinecone_api_key = os.environ.get("PINECONE_API_KEY")
        if pinecone_api_key and pinecone_api_key != "your_pinecone_api_key_here":
            self.pc = Pinecone(api_key=pinecone_api_key)
            self.index_name = "scentscape-descriptions"
            self._ensure_index()
        else:
            logger.warning("Pinecone API key not configured. Embeddings will not be uploaded.")
            self.pc = None

    def _ensure_index(self):
        """Ensure the Pinecone index exists, create if it doesn't."""
        existing_indexes = [index_info["name"] for index_info in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            logger.info(f"Creating Pinecone index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=self.model.get_sentence_embedding_dimension(),
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        self.index = self.pc.Index(self.index_name, pool_threads=30)

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Encode texts into vectors."""
        logger.info(f"Encoding {len(texts)} texts...")
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def process_and_upload(self, fragrances: List[Dict[str, Any]], batch_size: int = 500):
        """Generate embeddings for fragrance descriptions and upload to Pinecone."""
        if not self.pc:
            logger.warning("Pinecone client not initialized. Skipping upload.")
            return

        logger.info(f"Processing and parallel-uploading {len(fragrances)} fragrances...")
        
        texts_to_encode = []
        for frag in fragrances:
            text_features = [
                frag.get("name", ""),
                frag.get("brand", ""),
                frag.get("description", ""),
                " ".join(frag.get("top_notes", []) or []),
                " ".join(frag.get("middle_notes", []) or []),
                " ".join(frag.get("base_notes", []) or [])
            ]
            combined_text = " ".join(filter(None, text_features))
            fid = frag.get("id") or str(frag.get("name", "unk"))
            texts_to_encode.append((fid, combined_text, frag))

        async_results = []
        for i in range(0, len(texts_to_encode), batch_size):
            batch = texts_to_encode[i:i + batch_size]
            ids = [item[0] for item in batch]
            texts = [item[1] for item in batch]
            metadata_list = [item[2] for item in batch]
            
            embeddings = self.generate_embeddings(texts)
            vectors_to_upsert = []
            
            for frag_id, emb, meta in zip(ids, embeddings, metadata_list):
                cleaned_meta = {
                    "name": str(meta.get("name", "")),
                    "brand": str(meta.get("brand", "")),
                    "family": str(meta.get("family", "unknown")),
                }
                vectors_to_upsert.append({
                    "id": frag_id,
                    "values": emb,
                    "metadata": cleaned_meta
                })
            
            # Use async upsert via pool_threads
            logger.info(f"Queueing parallel upsert: batch {i//batch_size + 1}...")
            res = self.index.upsert(vectors=vectors_to_upsert, async_req=True)
            async_results.append(res)
            
        # Wait for all async requests to complete
        [r.get() for r in async_results]
        logger.info(f"Parallel upload of {len(fragrances)} vectors complete.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Check if seed fragrances exist
    seed_path = Path(__file__).parent.parent / "data" / "seed_fragrances.json"
    if seed_path.exists():
        with open(seed_path, "r", encoding="utf-8") as f:
            fragrances = json.load(f)
        
        encoder = TextEncoder()
        encoder.process_and_upload(fragrances)
    else:
        logger.error(f"Seed data not found at {seed_path}")
