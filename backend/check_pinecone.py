import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME", "Scentrix-fragrances")

print(f"Checking Pinecone Index: {index_name}")

if not api_key:
    print("Error: PINECONE_API_KEY not found in .env")
    exit(1)

pc = Pinecone(api_key=api_key)

try:
    indices = pc.list_indexes()
    print("Available Indices:")
    for idx in indices:
        print(f" - {idx.name}")
    
    if any(idx.name == index_name for idx in indices):
        print(f"\nSUCCESS: Index '{index_name}' exists.")
    else:
        print(f"\nFAILURE: Index '{index_name}' NOT found in your Pinecone project.")
except Exception as e:
    print(f"\nError connecting to Pinecone: {e}")
