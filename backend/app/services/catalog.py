import os
import logging
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

# Basic Config
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j_password")

_catalog_cache = None

def get_neo4j_client():
    if os.environ.get("RUNNING_IN_DOCKER") == "true":
        uri = "bolt://neo4j:7687"
    else:
        uri = NEO4J_URI
        
    try:
        driver = GraphDatabase.driver(uri, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        return driver
    except Exception as e:
        logger.error(f"Could not connect to Neo4j: {str(e)}")
        return None

def _load_from_neo4j() -> List[Dict[str, Any]]:
    driver = get_neo4j_client()
    if not driver:
        return []
        
    try:
        with driver.session() as session:
            # High-Fidelity Knowledge Graph Query (Aggregates relationships into canonical DNA)
            query = """
            MATCH (f:Fragrance)
            OPTIONAL MATCH (f)-[:HAS_NOTE]->(n:Note)
            OPTIONAL MATCH (f)-[:BELONGS_TO_ACCORD]->(a:Accord)
            WITH f, 
                 collect(DISTINCT {name: n.name, category: n.category}) as all_notes,
                 collect(DISTINCT a.name) as accords
            RETURN 
                f.id as id, 
                f.name as name, 
                f.brand as brand,
                [n in all_notes WHERE n.category = 'top' | n.name] as top_notes,
                [n in all_notes WHERE n.category = 'middle' | n.name] as middle_notes,
                [n in all_notes WHERE n.category = 'base' | n.name] as base_notes,
                accords,
                f.description as description,
                f.image_url as image_url,
                f.year as year,
                f.concentration as concentration,
                f.gender_label as gender_label,
                f.popularity as popularity
            """
            result = session.run(query)
            items = []
            for record in result:
                item = dict(record)
                if item.get("id"):
                    # Canonicalize lists to ensure UI reliability
                    for key in ["top_notes", "middle_notes", "base_notes", "accords"]:
                        val = item.get(key)
                        if not val:
                            item[key] = []
                    items.append(item)
            return items
    except Exception as e:
        logger.error(f"Error loading from Neo4j: {str(e)}")
        return []
    finally:
        driver.close()

import asyncio

def load_recommendation_catalog(force_reload: bool = False) -> List[Dict[str, Any]]:
    global _catalog_cache
    if _catalog_cache and not force_reload:
        return _catalog_cache
        
    neo4j_rows = _load_from_neo4j()
    if neo4j_rows:
        logger.info(f"Retrieved {len(neo4j_rows)} fragrances from Neo4j Graph.")
        _catalog_cache = neo4j_rows
        return _catalog_cache
        
    return []

async def load_recommendation_catalog_async(force_reload: bool = False) -> List[Dict[str, Any]]:
    """Non-blocking version of the catalog loader."""
    global _catalog_cache
    if _catalog_cache and not force_reload:
        return _catalog_cache
    
    # Run the synchronous Neo4j call in a separate thread to keep the event loop alive
    return await asyncio.to_thread(load_recommendation_catalog, force_reload)
