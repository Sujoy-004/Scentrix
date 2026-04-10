import os
import json
from neo4j import GraphDatabase

def diagnostic():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

    print(f"Connecting to SSOT (Neo4j) at {neo4j_uri}...")
    
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    with driver.session() as session:
        # Pull 5 random fragrances with their relationships
        cypher = """
        MATCH (f:Fragrance)-[r:HAS_NOTE|HAS_TOP_NOTE|HAS_MIDDLE_NOTE|HAS_BASE_NOTE]->(n:Note)
        RETURN type(r) as rel_type, count(r) as count
        UNION
        MATCH (f:Fragrance)-[r:BELONGS_TO_ACCORD]->(a:Accord)
        RETURN type(r) as rel_type, count(r) as count
        """
        result = session.run(cypher)
        items = [record.data() for record in result]
        
    print("\n--- NEURAL GRAPH DIAGNOSTIC RESULTS ---")
    print(json.dumps(items, indent=2))
    print("\n--- END DIAGNOSTIC ---")

if __name__ == "__main__":
    diagnostic()
