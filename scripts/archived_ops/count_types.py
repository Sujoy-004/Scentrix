import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def count_types():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    with driver.session() as session:
        # Int timestamps (new)
        result = session.run("MATCH (f:Fragrance) WHERE apoc.meta.type(f.updated_at) = 'INTEGER' RETURN count(f) as count")
        new_records = result.single()["count"]
        
        # String timestamps (old)
        result = session.run("MATCH (f:Fragrance) WHERE apoc.meta.type(f.updated_at) = 'STRING' RETURN count(f) as count")
        old_records = result.single()["count"]
        
        print(f"New Records (Integer TS): {new_records}")
        print(f"Old Records (String TS): {old_records}")
        
    driver.close()

if __name__ == "__main__":
    count_types()
