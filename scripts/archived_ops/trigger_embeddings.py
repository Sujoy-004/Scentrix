import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
import sys

# Add ml and backend to path
sys.path.append(os.path.abspath(os.curdir))

from ml.models.text_encoder import TextEncoder

load_dotenv()

def trigger_semantic_warmup():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    data_path = "ml/data/fra_elite_24k.json"
    print(f"--- ELITE RECOVERY DIRECTIVE: SEMANTIC WARM-UP (384D) ---")
    
    if not os.path.exists(data_path):
        print(f"ERROR: Dataset not found at {data_path}")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        fragrances = json.load(f)
    print(f"Loaded {len(fragrances)} fragrances for embedding calculation.")

    # Note: We should probably use the same stable IDs as Neo4j for vector IDs
    # I'll reuse the calculate_stable_id logic from the hydration script.
    from final_elite_hydration import calculate_stable_id
    
    for frag in fragrances:
        frag["id"] = calculate_stable_id(frag)

    # Initialize Encoder (all-MiniLM-L6-v2 -> 384D)
    try:
        encoder = TextEncoder()
        # The TextEncoder class handles the Pinecone upload too (based on env vars)
        # It uses fragrances, batch_size=100
        print("Starting pre-calculation and upload to Pinecone...")
        encoder.process_and_upload(fragrances, batch_size=200)
        print("Semantic Warm-up Complete.")
    except Exception as e:
        print(f"ERROR during Semantic Warm-up: {e}")

if __name__ == "__main__":
    trigger_semantic_warmup()
