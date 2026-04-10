import os
import time
import logging
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def profile_discovery_query():
    """Profile the most expensive discovery query for 24k nodes with 300ms target."""
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    with driver.session() as session:
        # 1. Complex Genetic Match Path (Fragrance -> Notes -> Other Fragrances)
        # 24k nodes, 355k edges.
        logger.info("PROFILING: Genetic Note Path (Depth 2 Discovery)")
        start = time.perf_counter()
        query = """
        MATCH (f:Fragrance)
        WITH f LIMIT 10
        MATCH (f)-[:HAS_NOTE]->(n:Note)<-[:HAS_NOTE]-(rec:Fragrance)
        WITH rec, count(n) as shared_notes
        WHERE shared_notes > 3
        RETURN rec.name as recommendation, shared_notes
        ORDER BY shared_notes DESC
        LIMIT 20
        """
        # We use profile prefix to get internal Neo4j execution plan if we had browser,
        # but here we just measure clock time.
        res = session.run(query)
        res.data()
        duration = (time.perf_counter() - start) * 1000
        logger.info(f"Duration: {duration:.2f}ms")

        if duration > 300:
            logger.warning(f"SLA BREACH: {duration:.2f}ms exceeds 300ms limit.")
        else:
            logger.info("SLA PASS: Graph Genetic Match is performant.")

    driver.close()

if __name__ == "__main__":
    profile_discovery_query()
