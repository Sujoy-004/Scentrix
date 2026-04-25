import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("PINECONE_API_KEY")

pc = Pinecone(api_key=api_key)

for name in ["scentscape-fragrances", "scentscape-graph"]:
    print(f"\n--- {name} ---")
    try:
        idx = pc.Index(name)
        print(f"Stats: {idx.describe_index_stats()}")
    except Exception as e:
        print(f"Error: {e}")
