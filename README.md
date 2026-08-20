# Scentrix

AI-driven fragrance discovery built for the cold-start problem: a 3-state "warmth" machine that turns a handful of ratings into good recommendations using precomputed GraphSAGE embeddings and feature-based scoring.

**Two commands to run. No Docker, no Postgres, no Redis, no Neo4j.**

---

## What it does

The system figures out how much it knows about a user and picks a matching recommendation strategy. That's the "warmth" state:

| State | Trigger | Strategy |
|---|---|---|
| **0 — Anonymous** | 0 ratings, no quiz taken | **Popularity** — the most-rated fragrances in the catalog |
| **1 — Cold** | Quiz submitted OR 1–2 ratings | **GraphSAGE user-vector + KNN** — your ratings are weighted into a 64-dim preference vector, then the nearest neighbors are found by cosine similarity |
| **2 — Warm** | 3+ ratings | **Feature-based Jaccard** — overlap scoring on notes, accords, family, occasion, and popularity |

Every state has a single safety net: if a strategy fails for any reason, the dispatcher falls back to popularity so the API never returns empty.

```
user ──▶ ratings ──▶ dispatcher ──▶ state (0 | 1 | 2)
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              popularity        GraphSAGE          feature-based
             (rating_count)   user-vector + KNN    Jaccard scoring
                    │                 │                 │
                    └─────────────▶ recommendations ◀──┘
```

---

## Architecture

Minimal by design — a FastAPI backend that owns all the logic, a Next.js frontend that calls it, and precomputed ML artifacts loaded as NumPy arrays.

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│  Next.js 16 (port 3000)     │  HTTP  │  FastAPI (port 8000)         │
│  home · quiz ·              │ ─────► │  auth · catalog · quiz ·     │
│  recommendations ·          │        │  recommendations · users     │
│  login · families           │        │                              │
└─────────────────────────────┘        │  dispatcher (3-state)        │
                                       │  SQLite (users + ratings)    │
                                       │  precomputed embeddings (.npy)│
                                       └──────────────────────────────┘
```

- **Backend** — FastAPI, sync SQLAlchemy, SQLite. Tables are created on startup; the quiz session store is a process-local dict (no Redis).
- **Frontend** — Next.js (App Router), 5 pages, talks to the API via `NEXT_PUBLIC_API_URL`.
- **ML artifacts** — a cleaned catalog JSON (4,559 fragrances) plus `[4559×64]` L2-normalized GraphSAGE embeddings shipped in `backend/app/data/`. No model is needed at serving time — only NumPy.
- **No external infra** — no Docker, Postgres, Neo4j, Redis, Supabase, Pinecone, or message queues.

---

## Quickstart

Prerequisites: **Python 3.11+**, **Node 20+**.

**1. Backend** (from `backend/`):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The API is now at http://localhost:8000 (`/health` responds `{"status": "success", "data": {...}}`).

**2. Frontend** (from `frontend/`):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

### Environment

- **Backend** reads `backend/.env`. Required values: `DATABASE_URL=sqlite:///./scentrix.db` and a `JWT_SECRET_KEY` (any long random string for dev). `backend/.env` is already present with working defaults.
- **Frontend** reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`). Copy `frontend/.env.example` to `frontend/.env.local` if you need to override it.

---

## API endpoints

All responses use a `{status, data}` envelope; recommendation responses also include `state`, `state_label`, and `source`.

| Method | Path | Purpose | Auth |
|---|---|---|---|
| POST | `/auth/register` | Create an account (returns JWT) | — |
| POST | `/auth/login` | Log in (returns JWT) | — |
| GET | `/auth/me` | Current user profile | Bearer |
| GET | `/fragrances/catalog` | Paginated catalog with search, brand/family/accord filters, sort | — |
| GET | `/fragrances/{id}` | Single fragrance detail | — |
| POST | `/fragrances/quiz/session/start` | Start a quiz session (seeds spanning olfactory families) | optional |
| POST | `/fragrances/quiz/session/{id}/answer` | Record one answer (in-memory) | optional |
| POST | `/fragrances/quiz/session/{id}/evaluate` | Compute confidence, decide if more questions are needed | optional |
| GET | `/fragrances/quiz/session/{id}/next-questions` | Next extension questions (uncertainty/diversity ranked) | optional |
| POST | `/fragrances/quiz/session/{id}/finalize` | Persist quiz ratings, mark quiz complete | Bearer |
| POST | `/fragrances/quiz/session/{id}/guest-finalize` | Finalize a guest quiz (no DB write) | optional |
| POST | `/recommendations/guest` | Guest recommendations through the 3-state dispatcher | — |
| POST | `/recommendations/rate` | Save a single rating (1–10) | Bearer |
| POST | `/recommendations/batch-rate` | Save many ratings at once | Bearer |
| GET | `/recommendations/personalized` | Recommendations from a user's stored ratings | Bearer |
| GET | `/users/profile` | Profile + rating count | Bearer |
| POST | `/users/preferences` | Merge stored preferences | Bearer |
| GET | `/health` | Health check incl. embedding-cache status | — |

---

## The ML bit

**What the embeddings are.** Fragrances that share notes and accords are linked into a Jaccard-similarity graph (same primary accord, edge if note-Jaccard > 0.2, top-k 10 neighbors). A 2-layer GraphSAGE is trained with a contrastive InfoNCE loss so each of the 4,559 catalog items gets a 64-dimensional, L2-normalized vector that encodes "who smells like me."

**How they're used at serving time.** No model inference, no PyTorch in the API. The embeddings are precomputed and shipped as a `.npy` file. When a cold user rates a few fragrances:

1. Each rating becomes a weight (`rating / 10`), and the weighted average of the rated items' embeddings becomes a **user vector** (L2-normalized).
2. Cosine similarity (a NumPy dot product) ranks all catalog items against that vector — a **KNN** search.
3. The top matches are hydrated with catalog metadata and returned.

If the embedding cache can't load (e.g., NumPy missing), the dispatcher automatically falls back to popularity.

**Regenerating the embeddings.** The training code lives in `backend/train.py` and is *not* part of the app requirements — it needs training-only dependencies (`torch`, `numpy`, `sentence-transformers`). It rebuilds the Jaccard graph, regenerates the 384-d text features, trains inline, validates (no NaN/Inf, exact `[4559×64]`, unit L2 norm), and overwrites the artifacts in `backend/app/data/`.

```bash
cd backend
pip install torch numpy sentence-transformers
python train.py                     # defaults: 100 epochs, all-MiniLM-L6-v2
python train.py --epochs 150 --skip-text   # reuse cached text embeddings
```

CLI args: `--epochs` (default 100), `--text-model` (default `all-MiniLM-L6-v2`), `--skip-text` (use cached `text_embeddings.npy`). The first run downloads the MiniLM model (~90 MB).

---

## Project structure

```
backend/
├── app/
│   ├── main.py               # FastAPI entry — mounts routers, /health, lifespan init
│   ├── config.py             # settings: DATABASE_URL, JWT_SECRET_KEY, CORS
│   ├── database.py           # sync SQLAlchemy engine + session (SQLite)
│   ├── models/models.py      # 2 tables: users, fragrance_ratings
│   ├── auth/
│   │   ├── auth.py           # bcrypt hashing + JWT create/verify
│   │   └── dependencies.py   # Bearer-token dependency (optional variant for quiz)
│   ├── routers/
│   │   ├── auth.py           # /auth/register, /auth/login, /auth/me
│   │   ├── catalog.py        # /fragrances/catalog, /fragrances/{id}
│   │   ├── quiz.py           # /fragrances/quiz/session/* (in-memory store)
│   │   ├── recommendations.py# /recommendations/* routed via dispatcher
│   │   └── users.py          # /users/profile, /users/preferences
│   ├── schemas/schemas.py    # Pydantic request/response models
│   └── services/
│       ├── dispatcher.py     # the 3-state warmth machine
│       ├── catalog.py        # loads + hydrates the JSON SSOT
│       ├── embeddings.py     # numpy user-vector + KNN (no torch)
│       ├── feature_based.py  # Jaccard note/accord scoring (warm state)
│       └── popularity.py     # rating_count ranking (anonymous state)
│
├── app/data/                 # serving artifacts
│   ├── scentrix_master_cleaned.json  # 4,559 fragrances (SSOT)
│   ├── node_embeddings_jaccard.npy   # [4559×64] float32 L2-normalized
│   └── node_ids_jaccard.json         # frag_ ids in catalog order
│
├── train.py                  # regenerates embeddings (training-only deps)
├── requirements.txt          # app dependencies (no torch)
└── pyproject.toml            # packaging, ruff/mypy/pytest config

frontend/
└── src/app/
    ├── page.tsx              # home / catalog landing
    ├── quiz/page.tsx         # adaptive preference quiz
    ├── recommendations/page.tsx
    ├── families/page.tsx     # browse fragrance families
    └── auth/login/page.tsx   # login
```

---

## Tests

```bash
cd backend
python -m pytest tests -q
```

The suite covers the dispatcher state transitions, user-vector + KNN behavior, feature-based scoring, auth, catalog loading, and the quiz flow.

---

## Notes / interview angles

- **Why 3 states?** Warmth is a gradient — unknown → quiz-cold → known. The earlier 5-state design added β-blends and diversity injection that complicated the code without defensible user value at this scale, so it was cut.
- **Why precomputed embeddings?** Cold-start recommendations don't change with every request — training once offline and serving a NumPy lookup makes the API fast, dependency-free (no PyTorch at runtime), and trivially reproducible via `train.py`.
- **Why no Docker?** The whole system runs on two processes (`uvicorn` + `next dev`). Docker orchestration for a single service each of backend and frontend was overhead, not value.
- **Own every line.** The codebase is intentionally small and fully understood — no framework boilerplate you can't explain.
- **Honest about the ML.** Embeddings give you "similar to what you rated"; once a user has enough ratings, interpretable feature overlap takes over. The system is honest about what each state can and can't do.