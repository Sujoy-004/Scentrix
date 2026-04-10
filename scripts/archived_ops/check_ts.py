import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def check_timestamps():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    with driver.session() as session:
        # Get count of records with today's date (April 7, 2026)
        # Note: Cypher timestamps are usually millis since epoch.
        # But we might have formatted dates or just check for presence.
        
        # Let's check the range of updated_at
        result = session.run("MATCH (f:Fragrance) RETURN min(f.updated_at) as min_ts, max(f.updated_at) as max_ts")
        res = result.single()
        print(f"Timestamp range: {res['min_ts']} to {res['max_ts']}")
        
        # Check how many have a certain property
        result = session.run("MATCH (f:Fragrance) WHERE f.updated_at IS NOT NULL RETURN count(f) as count")
        print(f"Records with updated_at: {result.single()['count']}")
        
    driver.close()

if __name__ == "__main__":
    check_timestamps()
