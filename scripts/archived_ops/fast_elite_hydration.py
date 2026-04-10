import os
import json
import hashlib
import time
from neo4j import GraphDatabase
from dotenv import load_dotenv
from typing import List, Dict, Any, Set

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

def execute_fast_elite_hydration():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")
    data_path = "ml/data/fra_elite_24k.json"

    print(f"--- ELITE RECOVERY DIRECTIVE: FAST HYDRATION ---")
    
    with open(data_path, "r") as f:
        elite_data = json.load(f)
    print(f"Loaded {len(elite_data)} records.")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    now_ms = int(time.time() * 1000)

    with driver.session() as session:
        # STEP 0: NEURAL FLUSH
        print("Neural Flush...")
        session.run("MATCH (n:Fragrance) DETACH DELETE n")
        # Optional: session.run("MATCH (n:Note) DETACH DELETE n")
        # Optional: session.run("MATCH (n:Accord) DETACH DELETE n")

        # STEP 1: PRE-PROCESS UNIQUE NOTES AND ACCORDS
        print("Extracting unique Notes and Accords...")
        all_notes: Set[str] = set()
        all_accords: Set[str] = set()
        for frag in elite_data:
            for n in frag.get("top_notes", []) + frag.get("middle_notes", []) + frag.get("base_notes", []):
                if n: all_notes.add(str(n))
            for a in frag.get("accords", []):
                if a: all_accords.add(str(a))
        
        print(f"Total Unique Notes: {len(all_notes)}")
        print(f"Total Unique Accords: {len(all_accords)}")

        # STEP 2: BATCH CREATE NOTES/ACCORDS
        print("Batch creating Notes and Accords...")
        note_list = list(all_notes)
        for i in range(0, len(note_list), 500):
            session.run("UNWIND $names as name MERGE (:Note {name: name})", {"names": note_list[i:i+500]})
            
        accord_list = list(all_accords)
        for i in range(0, len(accord_list), 500):
            session.run("UNWIND $names as name MERGE (:Accord {name: name})", {"names": accord_list[i:i+500]})

        # STEP 3: HYDRATE FRAGRANCES & LINKS
        print(f"Hydrating {len(elite_data)} Fragrances and creating relationships...")
        
        batch_size = 500
        for i in range(0, len(elite_data), batch_size):
            batch = elite_data[i:i+batch_size]
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
            
            # Using MATCH for notes/accords is much faster than MERGE after we pre-created them
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
            UNWIND frag.top_notes as note_name
            MATCH (nt:Note {name: note_name})
            CREATE (f)-[:HAS_NOTE {type: 'top'}]->(nt)
            
            WITH f, frag
            UNWIND frag.middle_notes as note_name
            MATCH (nm:Note {name: note_name})
            CREATE (f)-[:HAS_NOTE {type: 'middle'}]->(nm)
            
            WITH f, frag
            UNWIND frag.base_notes as note_name
            MATCH (nb:Note {name: note_name})
            CREATE (f)-[:HAS_NOTE {type: 'base'}]->(nb)
            
            WITH f, frag
            UNWIND frag.accords as accord_name
            MATCH (a:Accord {name: accord_name})
            CREATE (f)-[:BELONGS_TO_ACCORD]->(a)
            """, {"batch": processed_batch})
            
            if (i // batch_size) % 5 == 0:
                print(f"Done {i}/{len(elite_data)}...")

        print(f"\nFinal count check...")
        res = session.run("MATCH (f:Fragrance) RETURN count(f) as count")
        print(f"Final Brain Count: {res.single()['count']} / {len(elite_data)}")

    driver.close()

if __name__ == "__main__":
    execute_fast_elite_hydration()
