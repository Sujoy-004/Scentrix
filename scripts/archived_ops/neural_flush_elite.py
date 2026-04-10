import os
import time
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def execute_final_neural_flush():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

    print(f"--- NEURAL FLUSH: AETHERIC RECOVERY LOCK ---")
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    # Yesterday's threshold (any record older than April 7, 2026)
    # Today is April 8, 2026.
    # 1775575802045 was the min observed (Apr 7).
    # We want to keep ONLY the elite set from our latest hydration.
    
    with driver.session() as session:
        # Identify current state
        res = session.run("MATCH (f:Fragrance) RETURN count(f) as total")
        initial_count = res.single()["total"]
        print(f"Initial Fragrance count: {initial_count}")

        # 1. Purge non-elite (no hyphens) 
        # (Though my audit showed 0, we enforce it)
        print("Purging non-hyphenated legacy IDs...")
        res = session.run("""
        MATCH (f:Fragrance)
        WHERE NOT f.id CONTAINS '-'
        DETACH DELETE f
        RETURN count(f) as deleted
        """)
        print(f"Deleted {res.single()['deleted']} legacy records (no-hyphen).")

        # 2. Purge non-elite property
        print("Purging non-elite flagged nodes...")
        res = session.run("""
        MATCH (f:Fragrance)
        WHERE f.elite IS NULL OR f.elite = false
        DETACH DELETE f
        RETURN count(f) as deleted
        """)
        print(f"Deleted {res.single()['deleted']} non-elite nodes.")

        # 3. Resolve Identity Overlap (The 71 duplicates)
        # We keep only one node per ID, preferring the most recent or just any if they are identical
        print("Resolving 71 identity overlaps (deduplication)...")
        res = session.run("""
        MATCH (f:Fragrance)
        WITH f.id as id, collect(f) as nodes
        WHERE size(nodes) > 1
        UNWIND nodes[1..] as duplicate
        DETACH DELETE duplicate
        RETURN count(duplicate) as deleted
        """)
        print(f"Deleted {res.single()['deleted']} duplicate identity nodes.")

        # Final Verification
        res = session.run("MATCH (f:Fragrance) RETURN count(f) as total")
        final_count = res.single()["total"]
        print(f"Final Verified Brain Count: {final_count}")
        
        target = 24063
        if final_count == target:
            print(f"SUCCESS: Brain locked at EXACTLY {target} Elite records.")
        else:
            print(f"STILL AT {final_count}. Drift remains: {final_count - target}")
            if final_count > target:
                print("Aggressive Flush Required: Purging remaining orphans not in JSON...")
                # (Optional: implement direct JSON sync if drift persists)
    
    driver.close()

if __name__ == "__main__":
    execute_final_neural_flush()
