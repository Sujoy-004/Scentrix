import os
import json
from neo4j import GraphDatabase

def synchronize_seed_to_ssot():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

    print(f"Synchronizing Seed Data into Neo4j (SSOT) at {neo4j_uri}...")
    
    # Load seed data
    with open("ml/data/seed_fragrances.json", "r") as f:
        seed_data = json.load(f)

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    with driver.session() as session:
        for frag in seed_data:
            # Use MERGE to ensure items exist with their notes
            # This ensures the Quiz (which uses seed) matches the SSOT (Neo4j)
            session.run("""
                MERGE (f:Fragrance {id: $id})
                SET f.name = $name,
                    f.brand_id = $brand,
                    f.description = $description,
                    f.year = $year,
                    f.concentration = $concentration,
                    f.gender_label = $gender_label
                WITH f
                UNWIND $top_notes as note_name
                MERGE (nt:Note {name: note_name})
                MERGE (f)-[:HAS_TOP_NOTE]->(nt)
                WITH f
                UNWIND $accords as accord_name
                MERGE (a:Accord {name: accord_name})
                MERGE (f)-[:BELONGS_TO_ACCORD]->(a)
            """, frag)
            
    print(f"SSOT Alignment Complete. Synced {len(seed_data)} items.")

if __name__ == "__main__":
    synchronize_seed_to_ssot()
