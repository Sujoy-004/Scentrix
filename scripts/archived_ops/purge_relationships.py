import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def purge_duplicate_relationships():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

    print(f"--- RELATIONSHIP PURGE: 7.4M LEAK ---")
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    with driver.session() as session:
        # 1. Batch by Fragrance to avoid OOM
        print("Fetching Fragrance IDs...")
        res = session.run("MATCH (f:Fragrance) RETURN f.id as id")
        f_ids = [r["id"] for r in res]
        print(f"Loaded {len(f_ids)} fragrances.")

        batch_size = 500
        for i in range(0, len(f_ids), batch_size):
            batch = f_ids[i:i+batch_size]
            
            # Sub-batch relationship deletion
            session.run("""
            UNWIND $batch_ids as fid
            MATCH (f:Fragrance {id: fid})-[r:BELONGS_TO_ACCORD]->(a)
            WITH f, a, collect(r) as rs
            WHERE size(rs) > 1
            UNWIND rs[1..] as duplicate
            DELETE duplicate
            """, {"batch_ids": batch})

            session.run("""
            UNWIND $batch_ids as fid
            MATCH (f:Fragrance {id: fid})-[r:HAS_NOTE]->(n)
            WITH f, n, collect(r) as rs
            WHERE size(rs) > 1
            UNWIND rs[1..] as duplicate
            DELETE duplicate
            """, {"batch_ids": batch})

            if (i // batch_size) % 10 == 0:
                print(f"Processed {min(i+batch_size, len(f_ids))}/{len(f_ids)} fragrances...")

    # Final Verification
    with driver.session() as session:
        res = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
        print("Final Relationship Count:", [dict(r) for r in res])

    driver.close()

if __name__ == "__main__":
    purge_duplicate_relationships()
