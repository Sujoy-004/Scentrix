"""Neo4j graph ingestion for fragrance data.

Loads cleaned fragrance records into Neo4j, creating nodes and relationships.
Idempotent: running multiple times will not duplicate data (uses MERGE).
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from ml.graph import Neo4jClient

logger = logging.getLogger(__name__)


class FragranceGraphIngestor:
    """Ingests cleaned fragrance data into Neo4j graph."""

    def __init__(self, neo4j_client: Neo4jClient):
        """Initialize ingestor.

        Args:
            neo4j_client: Neo4j client instance
        """
        self.neo4j = neo4j_client
        self.stats = {
            "fragrances_created": 0,
            "fragrances_updated": 0,
            "notes_created": 0,
            "accords_created": 0,
            "brands_created": 0,
            "relationships_created": 0,
            "errors": 0,
        }

    def ingest_fragrances(self, fragrances: list[dict[str, Any]]) -> dict[str, Any]:
        """Ingest fragrance list into Neo4j.

        Idempotent: uses MERGE to avoid duplicates.

        Args:
            fragrances: Clean fragrance records

        Returns:
            Stats dict
        """
        logger.info(f"Starting ingestion of {len(fragrances)} fragrances")

        for i, frag in enumerate(fragrances):
            try:
                self._ingest_fragrance(frag)
                if (i + 1) % 50 == 0:
                    logger.info(f"Ingested {i + 1}/{len(fragrances)} fragrances")
            except Exception as e:
                logger.error(f"Error ingesting fragrance {frag.get('id')}: {e}")
                self.stats["errors"] += 1

        logger.info(
            f"Ingestion complete. Stats: {json.dumps(self.stats, indent=2)}"
        )
        return self.stats

    def _ingest_fragrance(self, frag: dict[str, Any]) -> None:
        """Ingest single fragrance record.

        Steps:
        1. Create/update Brand node
        2. Create/update Fragrance node
        3. Create/update Note nodes
        4. Create/update Accord nodes
        5. Create relationships: HAS_*_NOTE, BELONGS_TO_ACCORD, MADE_BY

        Args:
            frag: Fragrance record
        """
        frag_id = frag["id"]
        brand = frag["brand"]

        # Step 1: Ensure Brand exists
        brand_cypher = """
        MERGE (b:Brand {id: toLower($brand)})
        SET b.name = $brand
        RETURN b
        """
        try:
            self.neo4j.execute_query(brand_cypher, {"brand": brand})
            self.stats["brands_created"] += 1
        except Exception as e:
            logger.warning(f"Brand creation warning: {e}")

        # Step 2: Create/update Fragrance
        frag_cypher = """
        MERGE (f:Fragrance {id: toLower($id)})
        SET f.name = $name,
            f.brand_id = toLower($brand),
            f.year = $year,
            f.concentration = $concentration,
            f.gender_label = $gender_label,
            f.description = $description,
            f.updated_at = datetime()
        RETURN f
        """
        frag_params = {
            "id": frag_id,
            "name": frag["name"],
            "brand": brand,
            "year": frag.get("year"),
            "concentration": frag.get("concentration", ""),
            "gender_label": frag.get("gender_label", "N/A"),
            "description": frag.get("description", ""),
        }
        try:
            self.neo4j.execute_query(frag_cypher, frag_params)
            self.stats["fragrances_created"] += 1
        except Exception as e:
            logger.error(f"Fragrance creation error for {frag_id}: {e}")
            raise

        # Step 3: Create/update Notes and relationships
        for category, notes in [
            ("top", frag.get("top_notes", [])),
            ("middle", frag.get("middle_notes", [])),
            ("base", frag.get("base_notes", [])),
        ]:
            for position, note_name in enumerate(notes):
                self._ingest_note(frag_id, note_name, category, position)

        # Step 4: Create/update Accords and relationships
        for accord_name in frag.get("accords", []):
            self._ingest_accord(frag_id, accord_name)

        # Step 5: Link Fragrance to Brand
        brand_link_cypher = """
        MATCH (f:Fragrance {id: toLower($frag_id)})
        MATCH (b:Brand {id: toLower($brand)})
        MERGE (f)-[:MADE_BY]->(b)
        """
        try:
            self.neo4j.execute_query(
                brand_link_cypher,
                {"frag_id": frag_id, "brand": brand}
            )
            self.stats["relationships_created"] += 1
        except Exception as e:
            logger.warning(f"Brand link error: {e}")

    def _ingest_note(
        self,
        frag_id: str,
        note_name: str,
        category: str,
        position: int,
    ) -> None:
        """Ingest single note and create relationship.

        Args:
            frag_id: Fragrance ID
            note_name: Note display name
            category: "top", "middle", or "base"
            position: Position in category (0-indexed)
        """
        note_id = note_name.lower().replace(" ", "_")
        rel_type = f"HAS_{category.upper()}_NOTE"

        note_cypher = f"""
        MERGE (n:Note {{id: $note_id}})
        SET n.name = $note_name,
            n.category = $category
        WITH n
        MATCH (f:Fragrance {{id: toLower($frag_id)}})
        MERGE (f)-[r:{rel_type}]->(n)
        SET r.intensity = 1.0,
            r.position = $position
        RETURN n, r
        """
        try:
            self.neo4j.execute_query(
                note_cypher,
                {
                    "note_id": note_id,
                    "note_name": note_name,
                    "category": category,
                    "frag_id": frag_id,
                    "position": position,
                }
            )
            self.stats["notes_created"] += 1
            self.stats["relationships_created"] += 1
        except Exception as e:
            logger.warning(f"Note ingestion warning for {note_name}: {e}")

    def _ingest_accord(self, frag_id: str, accord_name: str) -> None:
        """Ingest accord and create relationship.

        Args:
            frag_id: Fragrance ID
            accord_name: Accord display name
        """
        accord_id = accord_name.lower().replace(" ", "_")

        accord_cypher = """
        MERGE (a:Accord {id: $accord_id})
        SET a.name = $accord_name
        WITH a
        MATCH (f:Fragrance {id: toLower($frag_id)})
        MERGE (f)-[r:BELONGS_TO_ACCORD]->(a)
        SET r.certainty = 1.0,
            r.weight = 1.0
        RETURN a, r
        """
        try:
            self.neo4j.execute_query(
                accord_cypher,
                {
                    "accord_id": accord_id,
                    "accord_name": accord_name,
                    "frag_id": frag_id,
                }
            )
            self.stats["accords_created"] += 1
            self.stats["relationships_created"] += 1
        except Exception as e:
            logger.warning(f"Accord ingestion warning for {accord_name}: {e}")

    def load_and_ingest(self, filepath: Path) -> dict[str, Any]:
        """Load cleaned JSON and ingest into Neo4j.

        Args:
            filepath: Path to cleaned fragrance JSON

        Returns:
            Stats dict
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                fragrances = json.load(f)
            if not isinstance(fragrances, list):
                fragrances = [fragrances]
            return self.ingest_fragrances(fragrances)
        except Exception as e:
            logger.error(f"Error loading file {filepath}: {e}")
            return self.stats


def ingest_fragrances_from_file(
    neo4j_client: Neo4jClient,
    input_path: Path,
) -> dict[str, Any]:
    """Standalone function to ingest fragrances.

    Args:
        neo4j_client: Neo4j client instance
        input_path: Path to cleaned JSON file

    Returns:
        Stats dict
    """
    ingestor = FragranceGraphIngestor(neo4j_client)
    return ingestor.load_and_ingest(input_path)


if __name__ == "__main__":
    import sys
    from ml.graph import init_neo4j

    if len(sys.argv) < 2:
        print("Usage: python ingest.py <input_json> [neo4j_uri] [neo4j_user] [neo4j_password]")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    neo4j_uri = sys.argv[2] if len(sys.argv) > 2 else "neo4j://localhost:7687"
    neo4j_user = sys.argv[3] if len(sys.argv) > 3 else "neo4j"
    neo4j_password = sys.argv[4] if len(sys.argv) > 4 else "password"

    # Initialize Neo4j and ingest
    client = init_neo4j(neo4j_uri, neo4j_user, neo4j_password)
    stats = ingest_fragrances_from_file(client, input_file)
    print(json.dumps(stats, indent=2))
