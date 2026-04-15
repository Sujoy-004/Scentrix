from neo4j import GraphDatabase
import sys

def check_neo4j():
    uri = "neo4j://localhost:7687"
    user = "neo4j"
    password = "neo4j_password"
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
        print("Neo4j: CONNECTED")
        
        with driver.session() as session:
            res = session.run("MATCH (n:Fragrance) RETURN count(n) as count")
            count = res.single()["count"]
            print(f"Fragrance Count: {count}")
            
    except Exception as e:
        print(f"Neo4j: FAILED ({e})")
        sys.exit(1)
    finally:
        driver.close()

if __name__ == "__main__":
    check_neo4j()
