import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def precreate_metadata():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")
    data_path = "ml/data/fra_elite_24k.json"

    with open(data_path, "r") as f:
        elite_data = json.load(f)

    all_notes = set()
    all_accords = set()
    for frag in elite_data:
        for n in frag.get("top_notes", []) + frag.get("middle_notes", []) + frag.get("base_notes", []):
            if n: all_notes.add(str(n))
        for a in frag.get("accords", []):
            if a: all_accords.add(str(a))
    
    print(f"Total Unique Notes: {len(all_notes)}")
    print(f"Total Unique Accords: {len(all_accords)}")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    # Pre-create Notes
    note_list = list(all_notes)
    with driver.session() as session:
        print("Ensuring unique constraints on Note(name)...")
        session.run("CREATE CONSTRAINT note_name IF NOT EXISTS FOR (n:Note) REQUIRE n.name IS UNIQUE")
        session.run("CREATE CONSTRAINT accord_name IF NOT EXISTS FOR (a:Accord) REQUIRE a.name IS UNIQUE")
        
        print(f"Loading {len(note_list)} Notes...")
        for i in range(0, len(note_list), 1000):
            batch = note_list[i:i+1000]
            session.run("UNWIND $batch as n MERGE (:Note {name: n})", {"batch": batch})
            print(f"Finished Note batch {i//1000 + 1}/{(len(note_list)-1)//1000 + 1}")
            
        accord_list = list(all_accords)
        print(f"Loading {len(accord_list)} Accords...")
        for i in range(0, len(accord_list), 1000):
            batch = accord_list[i:i+1000]
            session.run("UNWIND $batch as a MERGE (:Accord {name: a})", {"batch": batch})
            print(f"Finished Accord batch {i//1000 + 1}/{(len(accord_list)-1)//1000 + 1}")

    driver.close()
    print("Pre-creation done.")

if __name__ == "__main__":
    precreate_metadata()
