"""
full_ingest_24k.py — Final, idempotent 24k fragrance ingestion.

Steps:
  1. Enforce UNIQUE constraints on all node types.
  2. Deduplicate any existing duplicate nodes.
  3. Batch-ingest all 24,063 unique records into Neo4j using
     UNWIND+MERGE (fast bulk Cypher vs one-record-at-a-time).
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

# Ensure the repo root (inside the container /app) is on the path
sys.path.append(os.getenv("SCENTSCAPE_REPO_ROOT", "/app"))

from neo4j import GraphDatabase, basic_auth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("ingest_24k")

# ─── Config ───────────────────────────────────────────────────────────────────
NEO4J_URI      = "bolt://neo4j:7687"
NEO4J_USER     = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j_password")
DATA_FILE      = Path(os.getenv("SCENTSCAPE_REPO_ROOT", "/app")) / "ml" / "data" / "fra_elite_24k.json"
BATCH_SIZE     = 500   # records per Cypher UNWIND call


# ─── Driver ───────────────────────────────────────────────────────────────────
def get_driver():
    return GraphDatabase.driver(
        NEO4J_URI,
        auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD),
        max_connection_pool_size=20,
        connection_timeout=30.0,
    )


# ─── Step 1: Schema constraints ───────────────────────────────────────────────
CONSTRAINTS = [
    "CREATE CONSTRAINT fragrance_id_unique IF NOT EXISTS FOR (f:Fragrance) REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT note_id_unique      IF NOT EXISTS FOR (n:Note)      REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT accord_id_unique    IF NOT EXISTS FOR (a:Accord)    REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT brand_id_unique     IF NOT EXISTS FOR (b:Brand)     REQUIRE b.id IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX fragrance_rating IF NOT EXISTS FOR (f:Fragrance) ON (f.rating_value)",
    "CREATE INDEX fragrance_brand  IF NOT EXISTS FOR (f:Fragrance) ON (f.brand_id)",
]

def apply_schema(session):
    log.info("Applying schema constraints and indexes…")
    for stmt in CONSTRAINTS + INDEXES:
        try:
            session.run(stmt)
        except Exception as e:
            log.warning(f"Schema stmt skipped (may already exist): {e}")
    log.info("Schema ready.")


# ─── Step 2: Deduplication ────────────────────────────────────────────────────
DEDUP_QUERIES = [
    # For each duplicated (id), keep the oldest internal node, delete the rest
    """
    MATCH (f:Fragrance)
    WITH f.id AS id, collect(f) AS nodes
    WHERE size(nodes) > 1
    UNWIND nodes[1..] AS dup
    DETACH DELETE dup
    """,
    """
    MATCH (n:Note)
    WITH n.id AS id, collect(n) AS nodes
    WHERE size(nodes) > 1
    UNWIND nodes[1..] AS dup
    DETACH DELETE dup
    """,
    """
    MATCH (a:Accord)
    WITH a.id AS id, collect(a) AS nodes
    WHERE size(nodes) > 1
    UNWIND nodes[1..] AS dup
    DETACH DELETE dup
    """,
    """
    MATCH (b:Brand)
    WITH b.id AS id, collect(b) AS nodes
    WHERE size(nodes) > 1
    UNWIND nodes[1..] AS dup
    DETACH DELETE dup
    """,
]

def deduplicate(session):
    log.info("Deduplicating existing nodes…")
    for q in DEDUP_QUERIES:
        result = session.run(q)
        summary = result.consume()
        if summary.counters.nodes_deleted:
            log.info(f"  deleted {summary.counters.nodes_deleted} duplicate nodes")
    log.info("Deduplication complete.")


# ─── Step 3: Batch ingestion ──────────────────────────────────────────────────
UPSERT_FRAGRANCES = """
UNWIND $batch AS f
  MERGE (frag:Fragrance {id: f.id})
  SET frag.name           = f.name,
      frag.brand_id       = f.brand_id,
      frag.year           = f.year,
      frag.concentration  = f.concentration,
      frag.gender_label   = f.gender_label,
      frag.description    = f.description,
      frag.rating_value   = f.rating_value,
      frag.rating_count   = f.rating_count,
      frag.updated_at     = datetime()
  MERGE (brand:Brand {id: f.brand_id})
  SET brand.name = f.brand
  MERGE (frag)-[:MADE_BY]->(brand)
"""

UPSERT_NOTES = """
UNWIND $batch AS row
  MATCH (frag:Fragrance {id: row.frag_id})
  MERGE (n:Note {id: row.note_id})
  SET n.name = row.note_name, n.category = row.category
  WITH frag, n, row
  CALL apoc.merge.relationship(frag, row.rel_type, {}, {intensity: 1.0, position: row.position}, n) YIELD rel
  SET rel.position = row.position
"""

# Fallback without APOC — we'll detect it at runtime
UPSERT_TOP_NOTES    = """
UNWIND $batch AS row
  MATCH (frag:Fragrance {id: row.frag_id})
  MERGE (n:Note {id: row.note_id})
  SET n.name = row.note_name, n.category = 'top'
  MERGE (frag)-[r:HAS_TOP_NOTE]->(n)
  SET r.position = row.position
"""
UPSERT_MIDDLE_NOTES = """
UNWIND $batch AS row
  MATCH (frag:Fragrance {id: row.frag_id})
  MERGE (n:Note {id: row.note_id})
  SET n.name = row.note_name, n.category = 'middle'
  MERGE (frag)-[r:HAS_MIDDLE_NOTE]->(n)
  SET r.position = row.position
"""
UPSERT_BASE_NOTES   = """
UNWIND $batch AS row
  MATCH (frag:Fragrance {id: row.frag_id})
  MERGE (n:Note {id: row.note_id})
  SET n.name = row.note_name, n.category = 'base'
  MERGE (frag)-[r:HAS_BASE_NOTE]->(n)
  SET r.position = row.position
"""

UPSERT_ACCORDS = """
UNWIND $batch AS row
  MATCH (frag:Fragrance {id: row.frag_id})
  MERGE (a:Accord {id: row.accord_id})
  SET a.name = row.accord_name
  MERGE (frag)-[r:BELONGS_TO_ACCORD]->(a)
  SET r.weight = row.weight, r.certainty = 1.0
"""


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def load_data(filepath: Path) -> list[dict]:
    log.info(f"Loading {filepath} …")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        data = [data]
    # Deduplicate by id in-memory (JSON may have logical duplicates)
    seen = {}
    for rec in data:
        rid = rec.get("id")
        if rid and rid not in seen:
            seen[rid] = rec
    unique = list(seen.values())
    log.info(f"Total records in file  : {len(data)}")
    log.info(f"Unique-ID records       : {len(unique)}")
    return unique


def run_in_batches(session, query, batch_data, label="items"):
    total = len(batch_data)
    ingested = 0
    for chunk in chunks(batch_data, BATCH_SIZE):
        session.run(query, {"batch": chunk})
        ingested += len(chunk)
        log.info(f"  ✓ {ingested}/{total} {label}")


def ingest(session, fragrances: list[dict]):
    total = len(fragrances)
    log.info(f"=== Ingesting {total} fragrances ===")

    # ── Fragrance + Brand nodes ──────────────────────────────────────────────
    log.info("Pass 1/4 — Fragrance + Brand nodes…")
    frag_batch = [
        {
            "id":           f["id"],
            "name":         f.get("name", ""),
            "brand_id":     f.get("brand", "unknown").lower(),
            "brand":        f.get("brand", "unknown"),
            "year":         f.get("year"),
            "concentration":f.get("concentration", ""),
            "gender_label": f.get("gender_label", "unisex"),
            "description":  f.get("description", ""),
            "rating_value": f.get("rating_value", 0.0),
            "rating_count": f.get("rating_count", 0),
        }
        for f in fragrances
    ]
    run_in_batches(session, UPSERT_FRAGRANCES, frag_batch, "fragrances")

    # ── Notes ────────────────────────────────────────────────────────────────
    log.info("Pass 2/4 — Top/Middle/Base notes…")
    for note_type, query in [
        ("top_notes",    UPSERT_TOP_NOTES),
        ("middle_notes", UPSERT_MIDDLE_NOTES),
        ("base_notes",   UPSERT_BASE_NOTES),
    ]:
        note_batch = []
        for f in fragrances:
            for pos, note in enumerate(f.get(note_type, [])):
                note_batch.append({
                    "frag_id":   f["id"],
                    "note_id":   note.lower().replace(" ", "_"),
                    "note_name": note,
                    "position":  pos,
                })
        if note_batch:
            run_in_batches(session, query, note_batch, f"{note_type}")

    # ── Accords ──────────────────────────────────────────────────────────────
    log.info("Pass 3/4 — Accords…")
    accord_batch = []
    for f in fragrances:
        for idx, accord in enumerate(f.get("accords", [])):
            weight = max(0.4, 1.0 - idx * 0.2)
            accord_batch.append({
                "frag_id":    f["id"],
                "accord_id":  accord.lower().replace(" ", "_"),
                "accord_name":accord,
                "weight":     weight,
            })
    if accord_batch:
        run_in_batches(session, UPSERT_ACCORDS, accord_batch, "accord relationships")

    # ── Verify ───────────────────────────────────────────────────────────────
    log.info("Pass 4/4 — Verifying counts…")
    counts = {}
    for label in ["Fragrance", "Note", "Accord", "Brand"]:
        res = session.run(f"MATCH (n:{label}) RETURN count(n) as c")
        counts[label] = res.single()["c"]
    log.info(f"Final graph counts: {counts}")
    return counts


# ─── Entrypoint ───────────────────────────────────────────────────────────────
def main():
    if not DATA_FILE.exists():
        log.error(f"Data file not found: {DATA_FILE}")
        sys.exit(1)

    fragrances = load_data(DATA_FILE)
    driver = get_driver()

    t0 = time.time()
    with driver.session() as session:
        apply_schema(session)
        deduplicate(session)
        counts = ingest(session, fragrances)
    driver.close()

    elapsed = time.time() - t0
    log.info(f"=== Done in {elapsed:.1f}s ===")
    log.info(f"Fragrances in graph : {counts.get('Fragrance', '?')} / {len(fragrances)} unique")
    if counts.get("Fragrance", 0) >= len(fragrances):
        log.info("✅ 24k ingestion COMPLETE — Graph is fully hydrated.")
    else:
        log.warning("⚠️  Some records may have been skipped. Check logs above for errors.")


if __name__ == "__main__":
    main()
