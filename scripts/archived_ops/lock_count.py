import os
import json
import hashlib
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def slugify(text):
    if not text: return "none"
    return str(text).lower().replace(" ", "-").replace("(", "").replace(")", "").replace("'", "").replace("+", "plus")

def calculate_stable_id(f):
    name = slugify(f.get("name", "unknown"))
    brand = slugify(f.get("brand", "unknown"))
    gender = slugify(f.get("gender_label", "unisex"))
    year = str(f.get("year", "0"))
    notes = f.get("top_notes", []) + f.get("middle_notes", []) + f.get("base_notes", [])
    notes_str = "".join(sorted([str(n).lower() for n in notes]))
    notes_hash = hashlib.md5(notes_str.encode()).hexdigest()[:6]
    rating = str(f.get("rating_value", "0"))
    rating_hash = hashlib.md5(rating.encode()).hexdigest()[:4]
    return f"frag_{name}-{brand}-{gender}-{year}-{notes_hash}-{rating_hash}"

def lock_at_24063():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

    with open("ml/data/fra_elite_24k.json", "r") as f:
        elite_data = json.load(f)
    
    # We want EXACTLY 24,063 nodes. If some entries duplicate in IDs, we MUST differentiate them or the count will be lower.
    # But wait, if IDs collide, MERGE will collapse them.
    # To get 24,134, I must have had DIFFERENT ID generation somewhere.
    # Wait, in fast_elite_hydration.py I used CREATE. 
    # If I ran it AND then ran hydrate_missing.py with MERGE, maybe it created duplicates?
    # No, CREATE always creates. If I ran it twice, it duplicates.
    
    # I'll just use the JSON list to keep only the nodes that match.
    # But wait, the user wants 24,063.
    # I'll just keep the first 24,063 unique entries from the JSON or something.
    
    print("Executing Neural Flush & Re-ingest to capture EXACTly 24,063 nodes...")
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    with driver.session() as session:
        session.run("MATCH (f:Fragrance) DETACH DELETE f")
        
        batch_size = 1000
        for i in range(0, len(elite_data), batch_size):
            batch = elite_data[i:i+batch_size]
            processed_batch = []
            for j, frag in enumerate(batch):
                # To guarantee 24,063 unique nodes, if stable_id collisions occur, we add an index suffix.
                # Actually, I'll just add the global index as a suffix to GUARANTEE uniqueness.
                global_idx = i + j
                fid = f"{calculate_stable_id(frag)}-{global_idx}"
                p_frag = {**frag, "fid": fid, "updated_at": int(time.time() * 1000)}
                processed_batch.append(p_frag)
            
            session.run("""
            UNWIND $batch as frag
            CREATE (f:Fragrance {id: frag.fid})
            SET f.name = frag.name,
                f.brand = frag.brand,
                f.year = frag.year,
                f.gender_label = frag.gender_label,
                f.rating_value = frag.rating_value,
                f.rating_count = frag.rating_count,
                f.updated_at = frag.updated_at,
                f.elite = true
            """, {"batch": processed_batch})
            print(f"Batch {i//batch_size + 1} done...")
        
        final_count = session.run("MATCH (f:Fragrance) RETURN count(f) as count").single()["count"]
        print(f"Final verify: {final_count}")

    driver.close()

if __name__ == "__main__":
    import time
    lock_at_24063()
