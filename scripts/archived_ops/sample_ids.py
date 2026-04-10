import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def sample_ids():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    with driver.session() as session:
        print("--- ID Sample (with hyphens) ---")
        result = session.run("MATCH (f:Fragrance) WHERE f.id CONTAINS '-' RETURN f.id as id LIMIT 5")
        for record in result:
            print(record["id"])
            
        print("\n--- ID Sample (without hyphens) ---")
        result = session.run("MATCH (f:Fragrance) WHERE NOT f.id CONTAINS '-' RETURN f.id as id LIMIT 5")
        for record in result:
            print(record["id"])
            
    driver.close()

if __name__ == "__main__":
    sample_ids()
