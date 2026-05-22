---
phase: 01-pipeline-data-foundation
plan: 03
subsystem: backend, ml
tags: neo4j, graph-service, import-rewiring, lazy-init, thread-safety

# Dependency graph
requires:
  - phase: 01-pipeline-data-foundation
    plan: 02
    provides: Cleaned endpoints and frontend in fragrances.py (rewired get_graph_client)
provides:
  - Neo4j graph service at backend/app/services/graph.py with init_neo4j, get_neo4j, close_neo4j, Neo4jClient
  - All 5 files that previously imported from ml.graph now import from app.services.graph
affects: ml pipeline, data ingestion, graph population, seed_data

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Lazy singleton Neo4j driver with thread-safe lock (same pattern as catalog.py)
    - Graceful None fallback for Neo4j unavailability
    - Docker URI override (bolt://neo4j:7687) for container networking

key-files:
  created:
    - backend/app/services/graph.py
  modified:
    - backend/app/routers/fragrances.py
    - backend/scripts/seed_data.py
    - ml/flows/weekly_refresh.py
    - ml/tests/test_graph.py
    - ml/tests/test_integration.py

key-decisions:
  - Neo4jClient is a type alias for neo4j.Driver, falling back to Any when unavailable
  - _init_lock guards double-init race but avoids catalog.py's _load_lock (which protects cache loading)
  - Docker URI override follows exact catalog.py pattern for container networking
  - All ml/ files import from app.services.graph — works because Docker mounts backend at /app with PYTHONPATH=/app

patterns-established:
  - Graph service lazy-init: NOT required-at-startup, called lazily on first request
  - Try/except import guard for neo4j driver availability (same as catalog.py)
  - Thread-safe singleton with module-level lock

requirements-completed: []

# Metrics
duration: 5 min
completed: 2026-05-22
---

# Phase 01 Plan 03: Neo4j Graph Service + Import Rewiring Summary

**Neo4j graph service at backend/app/services/graph.py with init_neo4j, get_neo4j, close_neo4j, Neo4jClient type alias; all 5 files rewired from ml.graph to app.services.graph imports**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-22T09:14:36Z
- **Completed:** 2026-05-22T09:20:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Created `backend/app/services/graph.py` — Neo4j graph service with thread-safe lazy init, graceful None fallback, Docker URI override
- Exported `init_neo4j`, `get_neo4j`, `close_neo4j`, and `Neo4jClient` type alias
- Rewired `get_graph_client()` in `fragrances.py` — removed the sys.path hack and ml.graph dependency
- Removed unused `import os` and `import sys` from `fragrances.py`
- Updated 4 additional files: `seed_data.py`, `weekly_refresh.py`, `test_graph.py`, `test_integration.py`
- All 5 files now import cleanly from `app.services.graph` instead of the non-existent `ml.graph` module

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Neo4j graph service** - `a8dd665` (feat)
2. **Task 2: Rewire 5 files from ml.graph to app.services.graph** - `4df9600` (feat)

## Files Created/Modified

- `backend/app/services/graph.py` — New Neo4j graph service (init_neo4j, get_neo4j, close_neo4j, Neo4jClient)
- `backend/app/routers/fragrances.py` — Rewired get_graph_client(), removed unused imports
- `backend/scripts/seed_data.py` — Rewired import from ml.graph to app.services.graph
- `ml/flows/weekly_refresh.py` — Rewired import from ml.graph to app.services.graph
- `ml/tests/test_graph.py` — Rewired 2 imports from ml.graph to app.services.graph
- `ml/tests/test_integration.py` — Rewired import from ml.graph to app.services.graph

## Decisions Made

- Followed catalog.py lazy-singleton pattern with `_init_lock` for thread safety
- Docker URI override (bolt://neo4j:7687) when RUNNING_IN_DOCKER=true, matching catalog.py behavior
- ml/ files import from app.services.graph — works in Docker context (PYTHONPATH=/app, backend mounted at /app)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- None. All imports verified, ruff check and mypy pass for graph.py. Pre-existing mypy warnings in fragrances.py (return value type mismatches) are unrelated to this plan's changes.

## Next Phase Readiness

- Neo4j graph service ready for downstream consumers (ingestor, data population, graph validation)
- All dead ml.graph imports eliminated
- Ready for data preprocessing and graph population

---

*Phase: 01-pipeline-data-foundation*
*Completed: 2026-05-22*
