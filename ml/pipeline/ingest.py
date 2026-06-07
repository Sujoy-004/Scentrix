"""Fragrance graph ingestor — creates Neo4j nodes and edges from cleaned fragrance data."""

import json
import logging
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors

logger = logging.getLogger(__name__)

# --- Constants ---
SIMILARITY_K = 10
SIMILARITY_THRESHOLD = 0.5
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# --- KNN Similarity Computation ---


def compute_similarity_edges(fragrances: list[dict]) -> list[tuple[str, str, float]]:
    """Compute description embedding similarity.

    Uses SentenceTransformer all-MiniLM-L6-v2 to embed descriptions.
    KNN top-10 neighbors with cosine > 0.5 threshold.

    Args:
        fragrances: List of fragrance dicts with 'id' and 'description' keys.

    Returns:
        List of (id1, id2, score) tuples. Score is cosine similarity [0,1].
    """
    descriptions = [
        (f.get("description") or "") or (f.get("name") or "") for f in fragrances
    ]
    ids = [f.get("id", "") for f in fragrances]

    logger.info(f"Computing embeddings for {len(fragrances)} descriptions...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode(descriptions, show_progress_bar=True)

    logger.info("Computing KNN similarities...")
    nn = NearestNeighbors(
        n_neighbors=SIMILARITY_K + 1, metric="cosine", algorithm="brute"
    )
    nn.fit(embeddings)
    distances, indices = nn.kneighbors(embeddings)

    edges: list[tuple[str, str, float]] = []
    for i in range(len(fragrances)):
        for j in range(1, SIMILARITY_K + 1):  # skip self (index 0)
            neighbor_idx = indices[i][j]
            similarity = 1.0 - float(distances[i][j])
            if similarity > SIMILARITY_THRESHOLD:
                # Avoid duplicate edges: only add when i < neighbor_idx
                if i < neighbor_idx:
                    edges.append((ids[i], ids[neighbor_idx], similarity))

    logger.info(f"Generated {len(edges)} similarity edges")
    return edges


# --- Cypher Query Fragments ---

_CREATE_FRAGRANCE_NODE = """
MERGE (f:Fragrance {id: $id})
SET f.name = $name,
    f.brand = $brand,
    f.year = $year,
    f.description = $description,
    f.concentration = $concentration,
    f.gender_label = $gender_label
"""

_CREATE_BRAND_RELATIONSHIP = """
MERGE (f:Fragrance {id: $id})
MERGE (b:Brand {name: $brand})
MERGE (f)-[:MADE_BY]->(b)
"""

_CREATE_NOTE_RELATIONSHIP = """
FOREACH (note IN $notes |
    MERGE (n:Note {name: note, category: $category})
    MERGE (f)-[r:$REL_TYPE]->(n)
)
"""

_CREATE_ACCORD_RELATIONSHIP = """
FOREACH (accord IN $accords |
    MERGE (a:Accord {name: accord})
    MERGE (f)-[:BELONGS_TO_ACCORD]->(a)
)
"""

_CREATE_SIMILARITY_EDGE = """
MATCH (f1:Fragrance {id: $id1}), (f2:Fragrance {id: $id2})
MERGE (f1)-[s:SIMILAR_TO]->(f2)
SET s.score = $score
"""


# --- FragranceGraphIngestor ---


class FragranceGraphIngestor:
    """Ingests cleaned fragrance data into Neo4j.

    Creates nodes: Fragrance, Note (with category), Brand, Accord
    Creates edges: HAS_TOP_NOTE, HAS_MIDDLE_NOTE, HAS_BASE_NOTE,
                  BELONGS_TO_ACCORD, MADE_BY, SIMILAR_TO
    """

    def __init__(self, driver: Any):
        """Initialize with Neo4j driver instance.

        Args:
            driver: neo4j.Driver instance (or compatible). The ingestor accepts a driver
                   parameter directly and is self-contained — avoids circular import
                   issues when run from ml/ context.
        """
        self.driver = driver

    def ingest_fragrances(self, fragrances: list[dict]) -> dict[str, int]:
        """Create all nodes and relationships for the given fragrances.

        Args:
            fragrances: Cleaned fragrance dicts with fields:
                id, name, brand, year, description, concentration, gender_label,
                top_notes, middle_notes, base_notes, accords

        Returns:
            Dict with counts: fragrances_created, notes_created, accords_created,
                              brands_created, relationships_created, errors
        """
        stats: dict[str, int] = {
            "fragrances_created": 0,
            "notes_created": 0,
            "accords_created": 0,
            "brands_created": 0,
            "relationships_created": 0,
            "errors": 0,
        }

        with self.driver.session() as session:
            # Phase 1: Create fragrance nodes + brand/note/accord relationships
            for f in fragrances:
                try:
                    fid = f.get("id")
                    if not fid:
                        stats["errors"] += 1
                        continue

                    name = f.get("name", "") or ""
                    brand = f.get("brand", "Unknown") or "Unknown"
                    year = f.get("year")
                    description = f.get("description", "") or ""
                    concentration = f.get("concentration", "") or ""
                    gender_label = f.get("gender_label", "") or ""
                    top_notes = f.get("top_notes") or []
                    middle_notes = f.get("middle_notes") or []
                    base_notes = f.get("base_notes") or []
                    accords = f.get("accords") or []

                    # Create fragrance node
                    session.run(
                        _CREATE_FRAGRANCE_NODE,
                        id=fid,
                        name=name,
                        brand=brand,
                        year=year,
                        description=description,
                        concentration=concentration,
                        gender_label=gender_label,
                    )

                    # Create brand relationship
                    if brand and brand != "Unknown":
                        session.run(_CREATE_BRAND_RELATIONSHIP, brand=brand, id=fid)
                        stats["brands_created"] += 1

                    # Create note relationships
                    for note_list, rel_type, category in [
                        (top_notes, "HAS_TOP_NOTE", "top"),
                        (middle_notes, "HAS_MIDDLE_NOTE", "middle"),
                        (base_notes, "HAS_BASE_NOTE", "base"),
                    ]:
                        if note_list:
                            session.run(
                                f"""
                                MERGE (f:Fragrance {{id: $id}})
                                WITH f
                                UNWIND $notes AS note
                                MERGE (n:Note {{name: note, category: $category}})
                                MERGE (f)-[:{rel_type}]->(n)
                                """,
                                id=fid,
                                notes=list(
                                    dict.fromkeys(note_list)
                                ),  # dedup preserve order
                                category=category,
                            )
                            stats["notes_created"] += len(set(note_list))

                    # Create accord relationships
                    if accords:
                        session.run(
                            """
                            MERGE (f:Fragrance {id: $id})
                            WITH f
                            UNWIND $accords AS accord
                            MERGE (a:Accord {name: accord})
                            MERGE (f)-[:BELONGS_TO_ACCORD]->(a)
                            """,
                            id=fid,
                            accords=list(dict.fromkeys(accords)),  # dedup
                        )
                        stats["accords_created"] += len(set(accords))

                    stats["fragrances_created"] += 1

                except Exception as e:
                    logger.error(
                        f"Error ingesting fragrance {f.get('id', 'UNKNOWN')}: {e}"
                    )
                    stats["errors"] += 1

            # Phase 2: Compute and create similarity edges
            logger.info("Computing similarity edges...")
            try:
                similarity_edges = compute_similarity_edges(fragrances)
                for id1, id2, score in similarity_edges:
                    try:
                        session.run(
                            _CREATE_SIMILARITY_EDGE,
                            id1=id1,
                            id2=id2,
                            score=round(score, 4),
                        )
                        stats["relationships_created"] += 1
                    except Exception as e:
                        logger.error(f"Error creating similarity edge {id1}-{id2}: {e}")
                        stats["errors"] += 1
            except Exception as e:
                logger.error(f"Similarity computation failed: {e}")
                stats["errors"] += 1

        return stats


# --- Standalone Entry Point ---


def ingest_fragrances_from_file(
    driver: Any,
    filepath: Path,
) -> dict[str, int]:
    """Load cleaned fragrance JSON and ingest into Neo4j.

    Args:
        driver: Neo4j driver instance
        filepath: Path to cleaned fragrance JSON file

    Returns:
        Ingest statistics
    """
    with open(filepath, "r", encoding="utf-8") as f:
        fragrances = json.load(f)

    if not isinstance(fragrances, list):
        if isinstance(fragrances, dict):
            fragrances = [fragrances]
        else:
            raise ValueError(f"Expected list of fragrances, got {type(fragrances)}")

    logger.info(f"Loaded {len(fragrances)} fragrances from {filepath}")
    ingestor = FragranceGraphIngestor(driver)
    return ingestor.ingest_fragrances(fragrances)


# --- CLI Entry Point ---

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Ingest fragrance data into Neo4j")
    parser.add_argument("file", help="Path to cleaned fragrance JSON file")
    parser.add_argument("--uri", default="bolt://localhost:7687", help="Neo4j URI")
    parser.add_argument("--user", default="neo4j", help="Neo4j username")
    parser.add_argument("--password", default="neo4j_password", help="Neo4j password")
    args = parser.parse_args()

    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    try:
        stats = ingest_fragrances_from_file(driver, Path(args.file))
        print(f"Ingestion complete: {json.dumps(stats, indent=2)}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        driver.close()
