import os
from pinecone import Pinecone

def count_records():
    api_key = "pcsk_5rRt4U_HzNCEAggKws4zNnCySD4F9jpHCeEx2JF9pv7JsTA7r5fxfiXKFDJU8PFdR5TbQz"
    pc = Pinecone(api_key=api_key)
    
    index_name = "scentscape-descriptions"
    if index_name not in [idx.name for idx in pc.list_indexes()]:
        # Try the other name from .env
        index_name = "scentscape-fragrances"
        
    if index_name in [idx.name for idx in pc.list_indexes()]:
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        print(f"Index: {index_name}")
        print(f"Total Vector Count: {stats['total_vector_count']}")
    else:
        print("Required index not found.")

if __name__ == "__main__":
    count_records()
