import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def count_fragrances():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    with driver.session() as session:
        # Count all fragrances
        result = session.run("MATCH (f:Fragrance) RETURN count(f) as total")
        total = result.single()["total"]
        
        # Count elite fragrances (those with hyphens in ID)
        result = session.run("MATCH (f:Fragrance) WHERE f.id CONTAINS '-' RETURN count(f) as elite")
        elite = result.single()["elite"]
        
        # Count non-elite
        result = session.run("MATCH (f:Fragrance) WHERE NOT f.id CONTAINS '-' RETURN count(f) as non_elite")
        non_elite = result.single()["non_elite"]

    print(f"Total Fragrances: {total}")
    print(f"Elite (with hyphens): {elite}")
    print(f"Non-Elite (without hyphens): {non_elite}")
    driver.close()

if __name__ == "__main__":
    count_fragrances()
