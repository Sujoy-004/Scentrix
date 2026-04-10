import os
from pinecone import Pinecone

def check_indices():
    api_key = "pcsk_5rRt4U_HzNCEAggKws4zNnCySD4F9jpHCeEx2JF9pv7JsTA7r5fxfiXKFDJU8PFdR5TbQz"
    pc = Pinecone(api_key=api_key)
    
    print("\n--- PINECONE INDEX STATUS ---")
    active_indexes = pc.list_indexes()
    if not active_indexes:
        print("No indexes found.")
    else:
        for idx in active_indexes:
            print(f"Name: {idx.name}")
            print(f"Dimension: {idx.dimension}")
            print(f"Metrics: {idx.metric}")
            print(f"Host: {idx.host}")
            print("-" * 30)

if __name__ == "__main__":
    check_indices()
