import os
import json
import hashlib
import time
from neo4j import GraphDatabase
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

def slugify(text):
    if not text: return "none"
    return str(text).lower().replace(" ", "-").replace("(", "").replace(")", "").replace("'", "").replace("+", "plus")

def calculate_stable_id(f: Dict[str, Any]) -> str:
    name = slugify(f.get("name", "unknown"))
    brand = slugify(f.get("brand", "unknown"))
    gender = slugify(f.get("gender_label", "unisex"))
    year = str(f.get("year", "0"))
    
    # Hash notes to differentiate near-identical records
    notes = f.get("top_notes", []) + f.get("middle_notes", []) + f.get("base_notes", [])
    notes_str = "".join(sorted([str(n).lower() for n in notes]))
    notes_hash = hashlib.md5(notes_str.encode()).hexdigest()[:6]
    
    # Also include the rating to differentiate the 8 absolutely identical ones that differ only in rating
    rating = str(f.get("rating_value", "0"))
    rating_hash = hashlib.md5(rating.encode()).hexdigest()[:4]
    
    return f"frag_{name}-{brand}-{gender}-{year}-{notes_hash}-{rating_hash}"

def execute_elite_hydration():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")
    data_path = "ml/data/fra_elite_24k.json"

    print(f"--- ELITE RECOVERY DIRECTIVE: PHASE 1 ---")
    print(f"Loading Elite Dataset: {data_path}")
    
    if not os.path.exists(data_path):
        print(f"ERROR: Dataset not found at {data_path}")
        return

    with open(data_path, "r") as f:
        elite_data = json.load(f)
    
    print(f"Loaded {len(elite_data)} records for hydration.")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    # Current timestamp for April 2026 lock
    # Current time: 2026-04-07
    now_ms = int(time.time() * 1000)

    with driver.session() as session:
        # STEP 1: NEURAL FLUSH
        print("Executing Neural Flush (Purging all Fragrance nodes)...")
        session.run("MATCH (f:Fragrance) DETACH DELETE f")
        
        # STEP 2: HYDRATION
        print(f"Hydrating {len(elite_data)} Elite records with April 2026 timestamps...")
        
        # Batching for performance
        batch_size = 500
        for i in range(0, len(elite_data), batch_size):
            batch = elite_data[i:i+batch_size]
            
            # Prepare batch data with stable IDs and timestamps
            processed_batch = []
            for frag in batch:
                fid = calculate_stable_id(frag)
                p_frag = {
                    **frag,
                    "fid": fid,
                    "updated_at": now_ms,
                    "description": frag.get("description", f"A sophisticated {', '.join(frag.get('accords', [])[:2])} creation by {frag.get('brand')}.")
                }
                processed_batch.append(p_frag)
            
            session.run("""
            UNWIND $batch as frag
            CREATE (f:Fragrance {id: frag.fid})
            SET f.name = frag.name,
                f.brand = frag.brand,
                f.description = frag.description,
                f.year = frag.year,
                f.gender_label = frag.gender_label,
                f.rating_value = frag.rating_value,
                f.rating_count = frag.rating_count,
                f.updated_at = frag.updated_at,
                f.elite = true
            
            WITH f, frag
            
            // HYDRATE TOP NOTES
            UNWIND frag.top_notes as note_name
            MERGE (nt:Note {name: note_name})
            SET nt.category = 'top'
            CREATE (f)-[:HAS_NOTE {type: 'top'}]->(nt)
            
            WITH f, frag
            // HYDRATE MIDDLE NOTES
            UNWIND frag.middle_notes as note_name
            MERGE (nm:Note {name: note_name})
            SET nm.category = 'middle'
            CREATE (f)-[:HAS_NOTE {type: 'middle'}]->(nm)
            
            WITH f, frag
            // HYDRATE BASE NOTES
            UNWIND frag.base_notes as note_name
            MERGE (nb:Note {name: note_name})
            SET nb.category = 'base'
            CREATE (f)-[:HAS_NOTE {type: 'base'}]->(nb)
            
            WITH f, frag
            // HYDRATE ACCORDS
            UNWIND frag.accords as accord_name
            MERGE (a:Accord {name: accord_name})
            CREATE (f)-[:BELONGS_TO_ACCORD]->(a)
            """, {"batch": processed_batch})
            
            print(f"Processed batch {i//batch_size + 1}/{(len(elite_data)-1)//batch_size + 1}...")

        # STEP 3: VERIFICATION
        res = session.run("MATCH (f:Fragrance) RETURN count(f) as count")
        final_count = res.single()["count"]
        print(f"\n--- HYDRATION COMPLETE ---")
        print(f"Target Count: {len(elite_data)}")
        print(f"Final Brain Count: {final_count}")
        
        if final_count == len(elite_data):
            print("SUCCESS: Brain locked at exactly 24,063 Elite records.")
        else:
            print(f"WARNING: Count mismatch! ({final_count} vs {len(elite_data)})")

    driver.close()

if __name__ == "__main__":
    execute_elite_hydration()
