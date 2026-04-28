import json
import os
import sys
import logging
import numpy as np
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "data", "scentrix_master.json")
EMBEDDINGS_OUTPUT = os.path.join(BASE_DIR, "data", "embeddings.npy")
INDEX_OUTPUT = os.path.join(BASE_DIR, "data", "embedding_index.json")

def generate_embeddings():
    if not os.path.exists(DATASET_PATH):
        logger.error(f"Dataset not found at {DATASET_PATH}")
        return

    logger.info(f"Loading dataset from {DATASET_PATH}...")
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    logger.info(f"Loaded {len(catalog)} fragrances.")
    
    # Initialize model
    model_name = 'all-MiniLM-L6-v2'
    logger.info(f"Initializing SentenceTransformer model: {model_name}...")
    model = SentenceTransformer(model_name)

    texts = []
    ids = []
    
    for item in catalog:
        # Build text representation: name + brand + notes + accords + category
        name = item.get("name", "")
        brand = item.get("brand", "")
        notes = " ".join(item.get("top_notes", []) or [])
        accords = " ".join(item.get("accords", []) or [])
        category = item.get("category", "")
        
        text_rep = f"{name} {brand} {notes} {accords} {category}".strip()
        texts.append(text_rep)
        ids.append(str(item.get("id")))

    logger.info("Generating embeddings (this may take a few minutes)...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    # Save matrix
    logger.info(f"Saving embeddings to {EMBEDDINGS_OUTPUT}...")
    np.save(EMBEDDINGS_OUTPUT, embeddings)

    # Save index map: fragrance_id -> row index
    logger.info(f"Saving index map to {INDEX_OUTPUT}...")
    index_map = {fid: i for i, fid in enumerate(ids)}
    with open(INDEX_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(index_map, f)

    logger.info("Done!")

if __name__ == "__main__":
    generate_embeddings()
