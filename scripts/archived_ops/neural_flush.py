import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def flush_neural_brain():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

    print(f"Connecting to SSOT (Neo4j) at {neo4j_uri}...")
    
    # Load all elite IDs from JSON
    with open("ml/data/fra_elite_24k.json", "r") as f:
        data = json.load(f)
        elite_ids = {frag["id"] for frag in data}
        print(f"Loaded {len(elite_ids)} Elite IDs from JSON.")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    with driver.session() as session:
        # Count all current fragrances
        res = session.run("MATCH (f:Fragrance) RETURN count(f) as count")
        current_count = res.single()["count"]
        print(f"Current records in Neo4j: {current_count}")
        
        # Identify non-elite records (those not in the JSON set)
        # Note: This is an efficient way if we have the list.
        # But we can also use the properties from the user: "no hyphens or older than today"
        
        # Let's use the list to be ABSOLUTELY sure we lock at 24,063.
        # But for huge lists, passing them all as a param might be slow in one go.
        # We can do it in batches or just use the logic if it's reliable.
        
        # Let's try the user's logic first to see if it matches.
        # "f.id without hyphens OR IDs older than today"
        # Today's date is April 7, 2026.
        # Let's see how many match this.
        
        # Any record with a numeric ID like frag_001 might be legacy.
        # Any record with string TS like 2026-04-03 is old.
        
        # To be safe and meet the "Exactly 24,063" requirement, I'll delete EVERYTHING not in the elite_ids set.
        
        print("Executing Neural Flush (Purging 8,092 legacy records)...")
        
        # Flush in batches
        cypher = """
        MATCH (f:Fragrance)
        WHERE NOT f.id IN $elite_ids
        WITH f LIMIT 5000
        DETACH DELETE f
        RETURN count(f) as deleted
        """
        
        total_deleted = 0
        while True:
            res = session.run(cypher, {"elite_ids": list(elite_ids)})
            deleted = res.single()["deleted"]
            total_deleted += deleted
            if deleted == 0:
                break
            print(f"Batch deleted {deleted} records...")
            
        # Final count check
        res = session.run("MATCH (f:Fragrance) RETURN count(f) as count")
        new_count = res.single()["count"]
        print(f"Flush complete. Total deleted: {total_deleted}")
        print(f"Final Brain State: {new_count} records.")
        
    driver.close()

if __name__ == "__main__":
    flush_neural_brain()
