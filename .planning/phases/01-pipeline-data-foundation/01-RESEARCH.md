# Phase 1: Pipeline & Data Foundation — Research

**Researched:** 2026-05-15
**Domain:** Pipeline repair, Neo4j graph ingestion, data preprocessing, dead code removal
**Confidence:** HIGH

## Summary

Phase 1 fixes the broken Docker stack and makes fragrance graph data available for experiments. Four independent work streams: (1) Celery worker removal, (2) dead 503 endpoint cleanup + frontend scrub, (3) Neo4j graph service creation, (4) data preprocessing and graph population with similarity edges.

**Key insight:** The `ml/graph` module doesn't exist on disk despite being imported by 5 files. All graph functionality was aspirational — never connected. The new `backend/app/services/graph.py` creates it for real, and the new `ml/pipeline/ingest.py` populates it from the cleaned dataset.

**Primary recommendation:** Execute in dependency order: remove Celery (lowest risk) → remove dead endpoints → create graph service → create ingestor → preprocess + populate graph. Each step is independently testable.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Remove Celery entirely — delete worker container from docker-compose.yml, remove celery dependencies from pyproject.toml, delete any celery references in codebase. The worker only existed for async recommendation processing, which isn't needed for the research pipeline.
- **D-02:** Redis container and `redis` Python dependency remain (used by backend cache layer, future needs).
- **D-03:** Remove `recommend_by_text()` and `recommend_by_profile()` router methods from `backend/app/routers/fragrances.py`. Both immediately raise 503 with unreachable dead code below.
- **D-04:** Scrub corresponding frontend API calls from `frontend/src/lib/api.ts` and `frontend/src/lib/hooks.ts`.
- **D-05:** Create consolidated graph service at `backend/app/services/graph.py` with Neo4jClient, init_neo4j, close_neo4j, get_neo4j.
- **D-06:** Follow same pattern as catalog.py — lazy driver init, graceful None fallback, thread-safe lock, error logging. NOT required-at-startup.
- **D-07:** Create standalone `ml/pipeline/ingest.py` with `FragranceGraphIngestor` / `ingest_fragrances_from_file` following the pattern from `ml/tests/test_integration.py`.
- **D-08:** Update all imports across backend and ml that reference `ml.graph` and `ml.graph.neo4j_client` to point to the new `backend/app/services/graph.py`.
- **D-09:** Initial similarity edges built from description embedding cosine similarity using existing SentenceTransformer (`all-MiniLM-L6-v2` in `ml/models/text_encoder.py`).
- **D-10:** Hybrid approach: initial feature-based edges → Neo4j graph → GraphSAGE refines node embeddings → refined similarity edges written back.
- **D-11:** Edge density: KNN (top 10 neighbors) with minimum cosine similarity threshold (>0.5).
- **D-12:** Note relationships: `HAS_TOP_NOTE`, `HAS_MIDDLE_NOTE`, `HAS_BASE_NOTE` edges from fragrance to note nodes.
- **D-13:** Accord relationships: `BELONGS_TO_ACCORD` edges from fragrance to accord nodes.

### OpenCode's Discretion
- Preprocessing steps: run clean pipeline → validate with dataset_gate.py → output cleaned JSON for ingestion. Handle missing fields by skipping or filling with defaults — no complex imputation.
- Keep lazy-first-request loading as currently implemented. Don't re-enable commented-out warmup.

### Deferred Ideas (OUT OF SCOPE)
- Evaluation harness — Phase 2
- Baseline recommenders — Phase 3
- GraphSAGE evaluation wrapper — Phase 4
- Quiz → GraphSAGE integration — Phase 5
- MEXT demo page — Phase 6
- Full Celery replacement (if ever needed) — not on current roadmap
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-01 | Fix missing Celery worker module — create `celery_app.py` so Docker worker stops crashing | **Replaced by D-01**: Remove Celery entirely, not create celery_app.py |
| PIPE-02 | Rewire dead 503 endpoints (`recommend_by_text`, `recommend_by_profile`) — either implement or remove | **D-03/D-04**: Remove endpoints + scrub frontend calls |
| DATA-01 | Preprocess raw fragrance dataset: clean, normalize, construct Neo4j graph | Cleaner exists at `ml/pipeline/clean.py` — use as-is. New ingestor at `ml/pipeline/ingest.py` |
| DATA-02 | Build graph edges (fragrance-fragrance similarity, note relationships, note-fragrance) | D-09 through D-13 define edge schema. Similarity via SentenceTransformer embeddings + KNN |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Celery worker removal | Docker/Infra | — | Container + dependency cleanup, no code logic change |
| Endpoint removal | API/Backend | Frontend/Client | Remove router functions (backend), scrub API calls (frontend) |
| Graph service | API/Backend | — | Service layer in `backend/app/services/`, lazy-init, used by routers |
| Data preprocessing | ML Pipeline | — | Standalone `ml/pipeline/` scripts, runs offline |
| Graph ingestion | ML Pipeline | Database/Neo4j | Ingestor lives in ml/ but writes to Neo4j DB, uses backend graph service for connection |
| Similarity edge computation | ML Pipeline | — | Offline compute with SentenceTransformer embedding → KNN → Cypher writes |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| neo4j (Python driver) | >=5.14.0 | Neo4j graph database connectivity | Already in `pyproject.toml` under `[runtime]` and `[ml]` — verified dependency |
| sentence-transformers | >=3.0.0 | Description embeddings for similarity | Already in `pyproject.toml` under `[ml]` — model `all-MiniLM-L6-v2` used in `ml/models/text_encoder.py` |
| numpy | >=1.26.0,<2.0.0 | Embedding arrays, cosine similarity | Already in `pyproject.toml` under `[runtime]` |
| scikit-learn | (needs addition) | `neighbors.NearestNeighbors` for KNN | Needed for D-11 KNN top-10 neighbor search. Not in current deps — add to `[ml]` optional |
| redis | >=5.0.0 | Cache layer (keep) | D-02 keeps Redis — stays in `dependencies` in pyproject.toml |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| torch-geometric | >=2.4.0 | GraphSAGE (Phase 2+) | Not needed for Phase 1 — listed in `[ml]` for later |

**Installation:**
```bash
cd backend && pip install -e ".[dev,runtime,ml]"
```

**Version verification:** [VERIFIED: npm registry / PyPI via codebase]
- `neo4j>=5.14.0` [VERIFIED: pyproject.toml line 52]
- `sentence-transformers>=3.0.0` [VERIFIED: pyproject.toml line 58]
- `numpy>=1.26.0,<2.0.0` [VERIFIED: pyproject.toml line 50]

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────┐     ┌───────────────────────┐
│   docker-compose.yml │     │   Frontend (Next.js)  │
│                     │     │                       │
│  postgres  neo4j    │     │  api.ts hooks.ts      │
│  redis     backend  │────▶│  (scrub recommend/    │
│  ~~worker (REMOVE)~~│     │   text calls)         │
│  frontend           │     └───────────────────────┘
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                    │
│                                                      │
│  Routers: fragrances.py                              │
│    ├── recommend_by_text() ~~REMOVE~~                │
│    ├── recommend_by_profile() ~~REMOVE~~              │
│    ├── get_recommendation_result() ~~REMOVE~~          │
│    ├── get_graph_client() ~~REWRITE~~                  │
│    ├── list_fragrances() ─── uses graph client         │
│    ├── search_fragrances() ─── uses graph client       │
│    └── get_fragrance_detail() ─── uses graph client    │
│                                                      │
│  Services:                                            │
│    ├── catalog.py ─── (pattern to follow)             │
│    └── graph.py ─── NEW (Neo4jClient, init/close/get) │
│                                                      │
│  Config: sentry_config.py ~~REMOVE CeleryIntegration~~│
│          job_store.py ~~CLEAN celery_task_id~~         │
└─────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────┐
│               ML Pipeline (Standalone)               │
│                                                      │
│  1. ml/pipeline/clean.py  ─── FragranceDataCleaner    │
│     Input: scentrix_master.json (4577 records)       │
│     Output: cleaned_fragrances.json                   │
│                                                      │
│  2. ml/pipeline/dataset_gate.py ─── validation check │
│                                                      │
│  3. ml/pipeline/ingest.py  ─── NEW FragranceGraph     │
│     Ingestor                                          │
│     ├── Create Fragrance, Note, Brand, Accord nodes   │
│     ├── HAS_TOP_NOTE, HAS_MIDDLE_NOTE, HAS_BASE_NOTE   │
│     ├── BELONGS_TO_ACCORD, MADE_BY                    │
│     ├── Description embeddings (SentenceTransformer)  │
│     └── SIMILAR_TO edges (KNN top-10, >0.5 cosine)   │
│                                                      │
│  Output: Neo4j database ready for experiments         │
└─────────────────────────────────────────────────────┘

Data Flow (primary use case):
  scentrix_master.json ──▶ clean.py ──▶ dataset_gate.py ──▶ ingest.py ──▶ Neo4j
                                                                              │
  User search/request ──▶ FastAPI router ──▶ graph.py client ──▶ Neo4j query
                                                                              │
                                                                    Catalog cache
```

### Recommended Project Structure (Files Changed or Created)

```
docker-compose.yml              # REMOVE worker container (lines 100-135), CELERY env vars
backend/
├── pyproject.toml              # REMOVE celery dep (line 22)
├── app/
│   ├── main.py                 # Minor: router registration unchanged
│   ├── services/
│   │   └── graph.py            # CREATE: Neo4jClient, init/close/get_neo4j (per catalog.py pattern)
│   ├── routers/
│   │   └── fragrances.py       # REMOVE 2 endpoints, REWRITE get_graph_client, REMOVE get_recommendation_result
│   └── sentry_config.py        # REMOVE CeleryIntegration (lines 33-38)
├── scripts/
│   └── seed_data.py            # REWIRE: ml.graph → backend.app.services.graph
└── tests/
    └── test_recommendation_lifecycle.py  # REMOVE or UPDATE tests hitting dead endpoints

frontend/src/lib/
├── api.ts                      # REWRITE getFragranceCatalog to not call /recommend/text
└── hooks.ts                    # Check for references (none found for removed endpoints)

ml/
├── pipeline/
│   └── ingest.py               # CREATE: FragranceGraphIngestor + ingest_fragrances_from_file
├── flows/
│   └── weekly_refresh.py       # REWIRE: ml.graph → backend.app.services.graph
└── tests/
    ├── test_graph.py           # REWIRE: ml.graph → backend.app.services.graph
    └── test_integration.py     # REWIRE: ml.graph → backend.app.services.graph

Makefile                         # enrich target already references ingest.py (line 68)
```

### Pattern 1: Lazy Singleton Graph Client (from catalog.py)
**What:** Module-level singleton with thread-safe lazy initialization, graceful None fallback when Neo4j is unavailable.

**When to use:** For the new `backend/app/services/graph.py`. This is the established backend pattern.

**Pattern to follow (`backend/app/services/catalog.py`):**
```python
# Source: backend/app/services/catalog.py (verified pattern)
_driver = None
_load_lock = threading.Lock()

def get_neo4j_client():
    global _driver
    if _driver is not None:
        return _driver
    if not GraphDatabase:
        logger.warning("Neo4j driver not installed. Skipping graph connection.")
        return None
    try:
        _driver = GraphDatabase.driver(uri, auth=(user, password))
        return _driver
    except Exception as e:
        logger.error(f"Could not connect to Neo4j: {str(e)}")
        return None

def close_neo4j_client():
    global _driver
    if _driver:
        _driver.close()
        _driver = None
```

### Pattern 2: Graph Validation Cypher Queries (from test_graph.py)
**What:** Expected node types and relationship patterns.
**When to use:** When building the ingestor's Cypher queries.

```cypher
-- Node types: Fragrance, Note, Brand, Accord
-- Edge types: HAS_TOP_NOTE, HAS_MIDDLE_NOTE, HAS_BASE_NOTE, BELONGS_TO_ACCORD, MADE_BY, SIMILAR_TO

-- Create fragrance with properties (from test_integration.py pattern)
MATCH (f:Fragmentation {id: $id})
MERGE (f)-[:HAS_TOP_NOTE]->(n:Note {name: $note_name, category: 'top'})

-- SIMILAR_TO edges with score (from catalog.py pattern)
MATCH (f1:Fragrance {id: $id1}), (f2:Fragrance {id: $id2})
MERGE (f1)-[s:SIMILAR_TO {score: $score}]->(f2)
```

### Anti-Patterns to Avoid
- **sys.path manipulation for imports:** Current `get_graph_client()` in fragrances.py uses `sys.path.append(...)` then imports from `ml.graph.neo4j_client`. D-08 requires replacing this with proper imports from `backend.app.services.graph`.
- **Blocking startup:** D-06 explicitly says NOT required-at-startup. Keep lazy initialization.
- **Mutable global state without locks:** Always use `threading.Lock()` around the singleton pattern, as catalog.py does.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text embeddings | Custom TF-IDF or bag-of-words | `sentence-transformers` with `all-MiniLM-L6-v2` | Already in codebase (`ml/models/text_encoder.py`), 384-dim dense vectors, state-of-the-art semantic similarity |
| KNN search | Brute-force O(n²) similarity comparison | `sklearn.neighbors.NearestNeighbors` with cosine metric | Efficient top-k search, handles 4577 items easily, `n_neighbors=10` |
| Neo4j connection management | Raw driver without error handling | Lazy singleton with thread-safe lock (catalog.py pattern) | Graceful degradation when Neo4j is down, thread safety for concurrent requests |
| Description embedding generation | Re-computing on every request | Pre-compute + cache in `_catalog_embeddings_cache` | Already done in `hybrid_search.py`, should be reused by ingestor |

**Key insight:** The embedding computation is the most expensive part of this phase (4577 descriptions × 384-dim vectors). Pre-compute once during ingestion, store in the graph, never re-compute.

## Common Pitfalls

### Pitfall 1: The `get_encoder()` Dependency Chain
**What goes wrong:** The existing `TextEncoder` (in `ml.models.text_encoder`) requires `local_files_only=True` for SentenceTransformer. If the model isn't cached locally, initialization raises `RuntimeError`.

**Why it happens:** `TextEncoder.__init__` at `ml/models/text_encoder.py` line 27 uses `local_files_only=True`, which means the model must already be downloaded. In Docker, the model file may not exist.

**How to avoid:** The ingestor should use SentenceTransformer directly (not through TextEncoder), with `local_files_only=False` for first-time download, OR document a `make download-models` step. The ingestor runs standalone (not in Docker per se), so it can download the model on first run.

**Warning signs:** `"Local model 'all-MiniLM-L6-v2' is unavailable"` in logs.

### Pitfall 2: Circular Import Between ml/pipeline/ingest.py and backend/app/services/graph.py
**What goes wrong:** If `ml/pipeline/ingest.py` imports from `backend.app.services.graph`, and `graph.py` imports from `app.config`, the sys.path setup in Docker doesn't include the backend dir when running from ml/ context.

**Why it happens:** The ingestor runs both as `python -m ml.pipeline.ingest` (from ml/ context) and as `docker-compose exec backend python ml/pipeline/ingest.py` (from backend context with PYTHONPATH=/app). The sys.path differs between these.

**How to avoid:** Make the ingestor's Neo4j connection fully self-contained — accept `driver` or `uri/user/password` as parameters, don't import from `backend.app.services.graph`. The ingestor is a standalone script, not a backend service. Use a simple `neo4j.GraphDatabase.driver()` call directly, with the same graceful fallback pattern.

**Warning signs:** `ImportError` when running `python -m ml.pipeline.ingest` from ml/ directory.

### Pitfall 3: `ml/graph` Module Doesn't Exist
**What goes wrong:** 5 files import from `ml.graph` (`from ml.graph import Neo4jClient` etc.) but the directory `ml/graph/` doesn't exist on disk. These imports would fail at runtime.

**Why it happens:** The module was planned but never created — one of the known breakages.

**How to avoid:** D-08 requires rewiring all these imports to `backend.app.services.graph`. Create the new graph service first, then update all 5 import sites.

**Warning signs:** `ModuleNotFoundError: No module named 'ml.graph'` in logs when any of these files execute.

### Pitfall 4: Frontend `getFragranceCatalog` Has Complex Fallback Logic
**What goes wrong:** The function at `frontend/src/lib/api.ts` lines 41-71 has an `if (filters?.q)` branch that calls `/fragrances/recommend/text` (now 503/removed), polls `/fragrances/recommend/{job_id}` for results, and falls through to `/fragrances/catalog` only on failure. Simple removal of the dead-end branch breaks the text search feature.

**Why it happens:** The frontend was wired to use the async recommend/text endpoint for text search, which never worked (always 503).

**How to avoid:** Rewrite the `if (filters?.q)` branch to directly call `/fragrances/catalog?q=...`, which already supports text search via the `q` parameter (verified in fragrances.py `get_catalog` at line 235).

## Code Examples

### New Graph Service (`backend/app/services/graph.py`)

Following the exact pattern from `backend/app/services/catalog.py`:

```python
"""Neo4j graph client service — lazy init, graceful degradation."""
import logging
import os
import threading
from typing import Any, Optional

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None

from app.config import settings

logger = logging.getLogger(__name__)

_driver: Any = None
_init_lock = threading.Lock()


def init_neo4j(uri: Optional[str] = None, 
               user: Optional[str] = None, 
               password: Optional[str] = None) -> Any:
    """Initialize Neo4j driver. Thread-safe, idempotent."""
    global _driver
    if _driver is not None:
        return _driver

    if not GraphDatabase:
        logger.warning("Neo4j driver not installed.")
        return None

    uri = uri or settings.neo4j_uri
    user = user or settings.neo4j_user
    password = password or settings.neo4j_password

    # Docker URI override (same pattern as catalog.py line 32)
    if os.environ.get("RUNNING_IN_DOCKER") == "true" and uri == "neo4j://localhost:7687":
        uri = "bolt://neo4j:7687"

    with _init_lock:
        if _driver is not None:
            return _driver
        try:
            _driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info(f"Neo4j driver initialized: {uri}")
            return _driver
        except Exception as e:
            logger.error(f"Failed to init Neo4j driver: {e}")
            return None


def get_neo4j() -> Any:
    """Get existing Neo4j driver or None."""
    return _driver


def close_neo4j() -> None:
    """Close Neo4j driver."""
    global _driver
    if _driver:
        try:
            _driver.close()
        except Exception as e:
            logger.error(f"Error closing Neo4j driver: {e}")
        _driver = None
```

### Existing Graph Client to Replace (in `backend/app/routers/fragrances.py` lines 218-230)

```python
# THIS CODE IS REPLACED — sys.path hack + ml.graph import
def get_graph_client():
    """Lazy initialize neo4j client"""
    try:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
        from ml.graph.neo4j_client import get_neo4j, init_neo4j
        try:
            return get_neo4j()
        except RuntimeError:
            return init_neo4j(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    except Exception as exc:
        logger.error(f"Neo4j client init failed: {exc}")
        return None
```

### New Ingestor Signature (`ml/pipeline/ingest.py`)

Following the pattern from `ml/tests/test_integration.py` (which already uses `from ml.pipeline.ingest import FragranceGraphIngestor`):

```python
class FragranceGraphIngestor:
    """Ingests cleaned fragrance data into Neo4j."""
    
    def __init__(self, driver):
        self.driver = driver
    
    def ingest_fragrances(self, fragrances: list[dict]) -> dict:
        """Create nodes and relationships. Returns stats dict."""
        ...
    
    def _compute_similarity_edges(self, fragrances: list[dict]) -> list[tuple]:
        """Compute description embedding similarity via SentenceTransformer.
        
        Uses all-MiniLM-L6-v2 to embed descriptions.
        KNN top-10 neighbors, cosine > 0.5 threshold.
        Returns list of (id1, id2, score) tuples.
        """
        ...


def ingest_fragrances_from_file(driver, filepath: Path) -> dict:
    """Load cleaned JSON and ingest into Neo4j."""
    ...
```

### Verbose Cypher: Note/Accord/Fragrance Node Creation

```cypher
// Create or merge Fragrance node
MERGE (f:Fragrance {id: $id})
SET f.name = $name, f.brand = $brand, f.year = $year,
    f.description = $description, f.gender_label = $gender_label

// Create Brand node + relationship
MERGE (b:Brand {name: $brand})
MERGE (f)-[:MADE_BY]->(b)

// Create note nodes + typed relationships
FOREACH (note IN $top_notes |
    MERGE (n:Note {name: note, category: 'top'})
    MERGE (f)-[:HAS_TOP_NOTE]->(n)
)

// Create accord nodes + relationships
FOREACH (accord IN $accords |
    MERGE (a:Accord {name: accord})
    MERGE (f)-[:BELONGS_TO_ACCORD]->(a)
)

// SIMILAR_TO edges (bidirectional)
MATCH (f1:Fragrance {id: $id1}), (f2:Fragrance {id: $id2})
MERGE (f1)-[s:SIMILAR_TO]->(f2)
SET s.score = $score
MERGE (f2)-[s2:SIMILAR_TO]->(f1)
SET s2.score = $score
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Celery worker for async recs | No async processing — removed entirely | Phase 1 | Docker stack starts cleanly; no background task capability |
| `ml.graph` module (never existed) | `backend/app/services/graph.py` | Phase 1 | Graph client properly created, follows backend patterns |
| `get_graph_client()` with sys.path hack | Clean `backend.app.services.graph` import | Phase 1 | Removes sys.path manipulation, consistent service layer |
| Frontend text search via recommend/text | Direct `/fragrances/catalog?q=...` | Phase 1 | Works immediately, no polling, no 503 |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `sklearn.neighbors.NearestNeighbors` is the right KNN tool for D-11 | Code Examples | If sklearn not available, we'd need to brute-force — 4577 items fine for O(n²) once |
| A2 | `ml/pipeline/ingest.py` should NOT import from `backend.app.services.graph` | Common Pitfalls | If the ingestor is only ever called via Docker (where PYTHONPATH includes /app), a backend import might work; but standalone ml/ execution would break |
| A3 | SentenceTransformer `all-MiniLM-L6-v2` model can be downloaded on first run (not cached) | Pitfall 1 | If Docker has no network access, model download fails. Need `local_files_only=False` fallback or doc step |
| A4 | The `concentration` field is optional — data cleaner handles missing fields gracefully | Architecture | Cleaner in non-strict mode already warns on missing fields but continues (verified from clean.py source) |
| A5 | `get_recommendation_result()` endpoint (lines 787-864) should also be removed | Architecture | If some frontend code still polls this endpoint for unrelated features, removal would cause 404. Check: only `getFragranceCatalog` in api.ts references it via the polling loop on line 53 |
| A6 | `ingest_recommendation_interactions()` endpoint (lines 549-593) keeps working | Architecture | This endpoint has ongoing utility for logging interactions — no reason to remove it |

## Open Questions (RESOLVED)

1. **Should `get_recommendation_result()` (lines 787-864) also be removed?**
   - What we know: Only used by the frontend's `getFragranceCatalog` polling loop (api.ts lines 51-58), which is being rewritten to not use recommend/text at all. Removing the endpoint is clean but technically not in D-03's scope (which only names `recommend_by_text` and `recommend_by_profile`).
   - What's unclear: If any other code calls this endpoint.
   - Recommendation: Remove it. The endpoint only exists to poll for async job results that never complete (Celery is gone). Delete the function. If PIPE-02 says "implement or remove," removal is cleaner.

2. **Should `get_recommendation_weekly_metrics()` (lines 695-784) stay or go?**
   - What we know: Depends on `ingest_recommendation_interactions` for data. Not dead-coded (no 503). But used only for a feature that doesn't work end-to-end.
   - What's unclear: Whether the frontend or any UI consumes this metrics endpoint.
   - Recommendation: Keep it for now. Not broken, doesn't block startup, and interaction ingestion works independently. Can be cleaned up in a later phase.

3. **Do we need `scikit-learn` as a dependency?**
   - What we know: `sklearn.neighbors.NearestNeighbors` is the standard tool for KNN. Not currently in pyproject.toml.
   - Recommendation: Add `scikit-learn>=1.3.0` to `[ml]` optional deps. If sklearn is truly undesirable, brute-force O(n²) similarity works for 4577 items (4577*4576/2 ≈ 10.5M pairs, trivially fast). But sklearn's `NearestNeighbors` with `algorithm='brute'` is cleaner code. [ASSUMED]

## Environment Availability

> Phase 1 has external dependencies: Neo4j, Redis, Postgres (all Docker), and SentenceTransformer model download.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker + docker-compose | All services (Docker stack) | ✓ | v24+ | — |
| Neo4j 5 | Graph population, graph service | ✓ (docker) | 5-community | Lazy init returns None; catalog falls back to JSON SSOT |
| Redis 7 | Cache layer (D-02), job store | ✓ (docker) | 7-alpine | Caching degraded; job store errors |
| Postgres 15 | DB-backed features (auth, ratings) | ✓ (docker) | 15-alpine | DB-dependent features degrade |
| SentenceTransformer model | Description embeddings for similarity | *check* | all-MiniLM-L6-v2 | First run downloads model (requires internet) |
| Python 3.11+ | Backend + ML scripts | ✓ | 3.14.2 | — |
| scikit-learn | KNN for similarity edges (D-11) | *needs install* | — | Brute-force O(n²) pairs (4577 items fine) |
| Node.js 20+ | Frontend (cleanup only) | *not checked* | — | Only frontend file changes (no runtime dep needed) |

**Missing dependencies with no fallback:**
- None — all core services are Docker-based and provided via `docker-compose.yml`
- SentenceTransformer model may require first-time download (5min ~ 90MB)

**Missing dependencies with fallback:**
- scikit-learn — brute-force O(n²) cosine similarity for 4577 items (~10M comparisons) is acceptable for one-time ingestion
- Neo4j if offline — catalog falls back to JSON SSOT (existing pattern)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4+ (backend) / ml tests run standalone |
| Config file | `backend/pyproject.toml` (pytest config) |
| Quick run command | `docker-compose exec backend pytest tests/ -x --no-cov` |
| Full suite command | `make test-backend` (runs pytest --cov=app) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | Celery removed — worker container absent, imports don't reference celery | unit | Verify `docker-compose ps` has no worker; grep for `celery` in codebase | ❌ Wave 0 |
| PIPE-02 | Dead endpoints removed — recommend/text, recommend/profile return 404 | integration | `pytest tests/test_recommendation_lifecycle.py::test_text_recommend_requires_auth -x` | ❌ Wave 0 — existing test expects 401, will need update to 404 |
| DATA-01 | Data pipeline: clean → validate → ingest | integration | `python -m ml.tests.test_integration --profile local` | ❌ Wave 0 — test expected ml.graph to exist; needs rewiring |
| DATA-02 | Graph has expected nodes/edges | integration | `python -m ml.tests.test_graph --profile local` | ❌ Wave 0 — same ml.graph rewiring needed |

### Sampling Rate
- **Per task commit:** `docker-compose exec backend pytest tests/ -x --no-cov -k "not recommendation_lifecycle"`
- **Per wave merge:** `make test-backend` (backend tests) + `python -m ml.tests.test_integration --profile local` (ML pipeline)
- **Phase gate:** Both full suites green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `ml/tests/test_graph.py` — imports `from ml.graph import Neo4jClient` — needs rewiring to `backend.app.services.graph`
- [ ] `ml/tests/test_integration.py` — imports `from ml.graph import init_neo4j, close_neo4j` — needs rewiring
- [ ] `backend/tests/test_recommendation_lifecycle.py` — tests for `recommend/text` and `recommend/profile` hitting removed endpoints need removal/rewriting (lines 44-55, 57-80, 83-117, 120-140)
- [ ] No test yet for graph service itself — suggest adding `backend/tests/test_graph_service.py` for `init_neo4j`, `close_neo4j` graceful degradation

## Sources

### Primary (HIGH confidence)
- [VERIFIED: backend/app/services/catalog.py] — Lazy singleton pattern for graph service
- [VERIFIED: backend/app/routers/fragrances.py] — Dead endpoints at lines 504-546, 867-916; get_graph_client() at lines 218-230
- [VERIFIED: docker-compose.yml] — Worker container at lines 100-135; CELERY env vars at lines 70-71, 111-112
- [VERIFIED: backend/pyproject.toml] — celery dep at line 22; full dependency list
- [VERIFIED: ml/pipeline/clean.py] — FragranceDataCleaner pattern (389 lines)
- [VERIFIED: ml/models/text_encoder.py] — SentenceTransformer with all-MiniLM-L6-v2
- [VERIFIED: ml/tests/test_graph.py] — Expected graph schema, Cypher patterns
- [VERIFIED: ml/tests/test_integration.py] — Ingestor pattern, seed data loading
- [VERIFIED: frontend/src/lib/api.ts] — Frontend recommend/text call at line 44
- [VERIFIED: ml/data/scentrix_master.json] — 4577 records, all fields 100% coverage except concentration (0%)

### Secondary (MEDIUM confidence)
- [VERIFIED: backend/app/sentry_config.py lines 33-38] — CeleryIntegration import
- [VERIFIED: backend/app/services/job_store.py lines 52, 84] — celery_task_id field
- [VERIFIED: backend/tests/test_recommendation_lifecycle.py] — Tests for dead endpoints + celery_task_id refs
- [VERIFIED: backend/scripts/seed_data.py lines 10-11] — ml.graph imports
- [VERIFIED: ml/flows/weekly_refresh.py line 21] — ml.graph imports

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All libraries verified from pyproject.toml and existing code
- Architecture: HIGH — All patterns verified from existing code (catalog.py, test_integration.py)
- Pitfalls: HIGH — Each verified by reading the relevant source file

**Research date:** 2026-05-15
**Valid until:** Stable (30 days) — base libraries (neo4j, sentence-transformers) are stable

---

*Phase: 01-pipeline-data-foundation*
*Researched: 2026-05-15*
