import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("PINECONE_API_KEY")

pc = Pinecone(api_key=api_key)

for name in ["scentscape-fragrances", "scentscape-graph"]:
    try:
        idx_desc = pc.describe_index(name)
        print(f"Index: {name}, Dimension: {idx_desc.dimension}, Metric: {idx_desc.metric}")
    except Exception as e:
        print(f"Error describing {name}: {e}")
