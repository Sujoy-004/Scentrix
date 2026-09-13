# Scentrix Backend API

FastAPI-based REST API for fragrance discovery, preference collection via adaptive quiz and direct ratings, and 3-state recommendation serving.

## What It Does

- Fragrance catalog search and detail from the JSON source-of-truth (SQLite stores only users + ratings + quiz state)
- **3-state recommendation dispatcher** — ANONYMOUS → popularity, COLD → GraphSAGE user-vector KNN, WARM → feature-overlap scoring; popularity is the safety net in every state
- Direct ratings and an adaptive quiz feed the same preference profile; submitting a quiz pins the user to COLD regardless of rating count
- Offline-trained ML artifact serving — no runtime model, pure NumPy lookup
- Legacy local JWT auth (HS256) remains mounted for API compatibility, but the product is anonymous — catalog, quiz, and recommendation routes never require a token

## Stack

- **Framework:** FastAPI with Uvicorn
- **Database:** SQLite (sync SQLAlchemy) — users, ratings, quiz state
- **Catalog:** static JSON source-of-truth (`data/scentrix_master_cleaned.json`, 4,559 fragrances) loaded into memory
- **ML:** precomputed GraphSAGE embeddings shipped as artifacts in `app/data/`; no runtime model, no vector database
- **Auth:** legacy local JWT HS256 (python-jose), 15-minute expiry — kept mounted, unused by the demo app

## Local Development

```bash
# Install dependencies
pip install -e ".[dev]"          # runtime + dev/lint/test tooling
pip install -e ".[dev,ml]"       # + retraining/eval deps (torch, sentence-transformers, ranx)

# CPU-only torch (when no GPU is available)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Run dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Backend tests
pytest tests -q

# ML tests
pytest ml/tests -q

# Lint
ruff check . --fix
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, lifespan (SQLite init + embedding cache)
│   ├── config.py            # Pydantic settings (env-based)
│   ├── database.py          # Sync SQLAlchemy engine + sessions (SQLite)
│   ├── routers/             # auth, catalog, quiz, recommendations, users
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # dispatcher, embeddings, feature_based, popularity, catalog
│   ├── auth/                # JWT signing + dependencies
│   └── data/                # catalog JSON SSOT + ML artifacts (see below)
├── ml/
│   ├── tests/               # ML test suite
│   └── eval/                # offline cold-start eval harness + runs/
├── tests/                   # backend pytest suite
├── train.py                 # retrain script (writes app/data artifacts + metadata.json)
├── pyproject.toml
└── ruff.toml
```

## Recommendation Serving (3-state)

| State | Trigger | Strategy |
|-------|---------|----------|
| ANONYMOUS | 0 ratings, no quiz | popularity ranking |
| COLD | quiz submitted (any rating count) OR 1–2 ratings without a quiz | GraphSAGE user-vector KNN |
| WARM | 3+ ratings AND no quiz | weighted feature-overlap scoring |

- Quiz submission always overrides WARM (`quiz_submitted` takes precedence over rating count).
- Preference weights are centered and signed: `w = (rating − 5) / 5`, clamped to [−1, 1]. A 10 pulls the profile toward the item (+1.0), a 1 pushes it away (−1.0), and a neutral 5 contributes nothing.
- A profile with no usable signal (no ratings, or all-neutral ratings) falls back to popularity rather than fabricating a preference.
- Every state falls back to popularity so the API never returns empty.

## API Routes

| Prefix | Endpoints | Description |
|--------|-----------|-------------|
| `/auth` | register, login, me | Legacy user auth (HS256 JWT, 15 min) — not called by the app |
| `/fragrances` | /catalog, /{fragrance_id} | Catalog search + detail (JSON SSOT) |
| `/fragrances/quiz/session` | start, {id}/answer, {id}/evaluate, {id}/next-questions, {id}/finalize, {id}/guest-finalize | Adaptive quiz (guest flow uses guest-finalize) |
| `/recommendations` | /guest, /rate, /batch-rate, /personalized | 3-state serving; rating endpoints are legacy |
| `/users` | /profile, /preferences | Legacy user profile — not called by the app |
| `/health` | GET | Public health check incl. embedding-cache status |

See `/docs` when the backend is running for OpenAPI documentation.

## Service Architecture

| Service | Role |
|---------|------|
| `dispatcher.py` | 3-state routing (ANONYMOUS/COLD/WARM) with quiz-override precedence |
| `embeddings.py` | GraphSAGE artifact cache — weighted, L2-normalized user vector + KNN against precomputed 64-d embeddings |
| `feature_based.py` | WARM-state accord/note overlap scoring from rated items |
| `popularity.py` | ANONYMOUS ranking + safety-net fallback |
| `catalog.py` | JSON SSOT loader, search, family/accord filtering |

## ML Artifacts (`app/data/`)

- `node_embeddings_jaccard.npy` — [4559×64] L2-normalized GraphSAGE embeddings (offline-trained)
- `node_ids_jaccard.json` — catalog-id order matching the embedding rows
- `text_embeddings.npy` + `text_embeddings.hash.json` — MiniLM text features used at training time
- `metadata.json` — reproducibility record: training settings, validation gates (all passing), catalog SHA-256
- `scentrix_master_cleaned.json` — catalog source of truth (4,559 fragrances)

Serving never loads torch; the embeddings are read as NumPy — "the artifacts are the model." Retrain with `python train.py`, which validates its outputs, writes `metadata.json`, and atomically replaces the artifacts. Offline cold-start evaluation lives in `ml/eval/` (protocol in `ml/eval/README-COLD-START.md`, recorded runs in `ml/eval/runs/`). Honesty note: it is an intrinsic, content-oracle proxy — there is no real user-interaction data in the repo.

## Configuration

Key environment variables (see `.env.example`):

- `DATABASE_URL` — SQLite by default (`sqlite:///./scentrix.db`)
- `JWT_SECRET_KEY` — HS256 signing secret
- `JWT_ALGORITHM` — default `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES` — default `15`
- `ALLOWED_ORIGINS` — comma-separated CORS origins