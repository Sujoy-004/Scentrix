import os
import json
from neo4j import GraphDatabase

def deep_neural_alignment():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

    print(f"Executing Deep Neural SSOT Alignment at {neo4j_uri}...")
    
    # Load all 50 items with full metadata
    with open("ml/data/seed_fragrances.json", "r") as f:
        seed_data = json.load(f)

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    with driver.session() as session:
        for frag in seed_data:
            # We must ensure BOTH frag_001 and frag_syn_001 exist and share the same DNA
            # This covers both old synthetic lookups and new seed lookups
            id_variations = [frag['id'], frag['id'].replace("frag_", "frag_syn_")]
            
            for fid in id_variations:
                session.run("""
                    MERGE (f:Fragrance {id: $fid})
                    SET f.name = $name,
                        f.brand_id = $brand,
                        f.description = $description,
                        f.year = $year,
                        f.concentration = $concentration,
                        f.gender_label = $gender_label,
                        f.updated_at = timestamp()
                    WITH f
                    
                    // PURGE STALE NEURAL LINKS
                    OPTIONAL MATCH (f)-[old:HAS_TOP_NOTE|HAS_MIDDLE_NOTE|HAS_BASE_NOTE|BELONGS_TO_ACCORD]->()
                    DELETE old
                    WITH f
                    
                    // RE-HYDRATE TOP NOTES
                    UNWIND $top_notes as note_name
                    MERGE (nt:Note {name: note_name})
                    MERGE (f)-[:HAS_TOP_NOTE]->(nt)
                    WITH f
                    
                    // RE-HYDRATE ACCORDS
                    UNWIND $accords as accord_name
                    MERGE (a:Accord {name: accord_name})
                    MERGE (f)-[:BELONGS_TO_ACCORD]->(a)
                """, {**frag, "fid": fid})
                
    print(f"Deep SSOT Alignment Complete. Cross-referenced all ID variations.")

if __name__ == "__main__":
    deep_neural_alignment()
