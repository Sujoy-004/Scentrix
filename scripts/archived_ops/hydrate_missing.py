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
    notes = f.get("top_notes", []) + f.get("middle_notes", []) + f.get("base_notes", [])
    notes_str = "".join(sorted([str(n).lower() for n in notes]))
    notes_hash = hashlib.md5(notes_str.encode()).hexdigest()[:6]
    rating = str(f.get("rating_value", "0"))
    rating_hash = hashlib.md5(rating.encode()).hexdigest()[:4]
    return f"frag_{name}-{brand}-{gender}-{year}-{notes_hash}-{rating_hash}"

def hydrate_missing():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")
    
    with open("ml/data/fra_elite_24k.json", "r") as f:
        elite_data = json.load(f)

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    now_ms = int(time.time() * 1000)

    with driver.session() as session:
        # Get existing IDs
        print("Fetching existing IDs in Neo4j...")
        res = session.run("MATCH (f:Fragrance) RETURN f.id as id")
        existing_ids = {r["id"] for r in res}
        print(f"Found {len(existing_ids)} existing records.")
        
        missing = [f for f in elite_data if calculate_stable_id(f) not in existing_ids]
        print(f"Remaining to hydrate: {len(missing)} records.")
        
        if not missing:
            print("Everything hydrated!")
            return

        batch_size = 500
        for i in range(0, len(missing), batch_size):
            batch = missing[i:i+batch_size]
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
            MERGE (f:Fragrance {id: frag.fid})
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
            MERGE (nt:Note {name: note_name})
            CREATE (f)-[:HAS_NOTE {type: 'top'}]->(nt)
            
            WITH f, frag
            UNWIND frag.middle_notes as note_name
            MERGE (nm:Note {name: note_name})
            CREATE (f)-[:HAS_NOTE {type: 'middle'}]->(nm)
            
            WITH f, frag
            UNWIND frag.base_notes as note_name
            MERGE (nb:Note {name: note_name})
            CREATE (f)-[:HAS_NOTE {type: 'base'}]->(nb)
            
            WITH f, frag
            UNWIND frag.accords as accord_name
            MERGE (a:Accord {name: accord_name})
            CREATE (f)-[:BELONGS_TO_ACCORD]->(a)
            """, {"batch": processed_batch})
            print(f"Hyderated batch {i//batch_size + 1}...")

    driver.close()

if __name__ == "__main__":
    hydrate_missing()
