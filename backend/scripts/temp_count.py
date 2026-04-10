import os
from neo4j import GraphDatabase

def count_relationships():
    neo4j_uri = "neo4j://neo4j:7687"
    neo4j_user = "neo4j"
    neo4j_password = "neo4j_password"

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    with driver.session() as session:
        # Count all relationships
        result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
        total = result.single()["total"]
        
        # Count notes
        result = session.run("MATCH ()-[r:HAS_NOTE]->() RETURN count(r) as notes")
        notes = result.single()["notes"]

        # Count accords
        result = session.run("MATCH ()-[r:BELONGS_TO_ACCORD]->() RETURN count(r) as accords")
        accords = result.single()["accords"]
        
    print(f"Total Relationships: {total}")
    print(f"Note Relationships: {notes}")
    print(f"Accord Relationships: {accords}")
    driver.close()

if __name__ == "__main__":
    count_relationships()
