# Scentrix

AI-driven fragrance discovery built for the cold-start problem: a 3-state "warmth" machine that turns a handful of ratings into good recommendations using precomputed GraphSAGE embeddings and feature-based scoring.

**One command to run. No Docker, no Postgres, no Redis, no Neo4j.**

---

## What it does

The system figures out how much it knows about a user and picks a matching recommendation strategy. That's the "warmth" state:

| State | Trigger | Strategy |
|---|---|---|
| **0 — Anonymous** | 0 ratings, no quiz taken | **Popularity** — the most-rated fragrances in the catalog |
| **1 — Cold** | Quiz submitted (any rating count) OR 1–2 ratings with no quiz | **GraphSAGE user-vector + KNN** — each rating contributes a signed weight `(rating − 5) / 5` to a 64-dim preference vector; nearest neighbors are found by cosine similarity |
| **2 — Warm** | 3+ ratings with no quiz | **Feature-based Jaccard** — overlap scoring on notes, accords, family, occasion, and popularity |

State precedence: a submitted quiz always routes to the Cold (embedding) path — the quiz answers are the strongest cold-start signal we have — even if the user also has 3+ ratings. Warm only applies to organic (non-quiz) ratings.

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
│  home · quiz ·              │ ─────► │  catalog · quiz ·            │
│  recommendations ·          │        │  recommendations · users     │
│  families · fragrance detail│        │  (auth/* kept as legacy)     │
└─────────────────────────────┘        │  dispatcher (3-state)        │
                                       │  SQLite (users + ratings)    │
                                       │  precomputed embeddings (.npy)│
                                       └──────────────────────────────┘
```

- **Backend** — FastAPI, sync SQLAlchemy, SQLite. Tables are created on startup; the quiz session store is a process-local dict (no Redis).
- **Frontend** — Next.js (App Router), anonymous-first: the product never asks for an account. It talks to the API via `NEXT_PUBLIC_API_URL`.
- **ML artifacts** — a cleaned catalog JSON (4,559 fragrances) plus `[4559×64]` L2-normalized GraphSAGE embeddings, an ID index, and a `metadata.json` validation record shipped in `backend/app/data/`. No model is needed at serving time — only NumPy.
- **No external infra** — no Docker, Postgres, Neo4j, Redis, Supabase, Pinecone, or message queues.

> **Auth is retired.** Login was removed from the product, so the `/auth/*` router no longer exists and the app starts without any JWT configuration. The app you see at `localhost:3000` is fully anonymous — catalog, quiz, and recommendations never require a token, so the frontend sends none. (Legacy Bearer-protected helpers on `/users/*` and the rating endpoints remain mounted but are never called.)

---

## Quickstart

Prerequisites: **Python 3.11+**, **Node 20+**, PowerShell 7+.

### Option A — one command (Windows)

From the repo root, the bundled script sets up a fresh venv, installs backend deps,
then launches **both** servers in two windows:

```powershell
.\start.ps1
```

Backend → http://localhost:8000 (`/docs` for the interactive API explorer) ·
Frontend → http://localhost:3000.

### Option B — two terminals (manual)

**1. Backend** (from `backend/`):

```bash
cd backend
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt   # Windows
# macOS/Linux: source venv/bin/activate && pip install -r requirements.txt
venv\Scripts\python.exe -m uvicorn app.main:app --reload     # Windows
# macOS/Linux: python -m uvicorn app.main:app --reload
```

The API is now at http://localhost:8000 (`/health` responds `{"status": "success", "data": {...}}`).

**2. Frontend** (from `frontend/`):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The product is anonymous-only — no account, login, or sign-up anywhere in the flow.

> Windows note: always call the interpreter as `venv\Scripts\python.exe -m pip …`.
> A bare `venv\Scripts\pip` is misread by PowerShell as `Module\Command` and fails.

### Environment

- **Backend** runs with no env file. `DATABASE_URL` defaults to a local SQLite file (`sqlite:///./scentrix.db`). Authentication is retired from the product (no login), so no `JWT_SECRET_KEY` is required to start.
- **Frontend** reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`). Copy `frontend/.env.example` to `frontend/.env.local` only if you need to override it.

---

## API endpoints

All responses use a `{status, data}` envelope; recommendation responses also include `state`, `state_label`, and `source`. The demo flow is entirely anonymous — the retired `/auth` endpoints were removed and the app never calls the Bearer-protected helpers below.

| Method | Path | Purpose | Auth |
|---|---|---|---|
| GET | `/fragrances/catalog` | Paginated catalog with search, brand/family/accord filters, sort | — |
| GET | `/fragrances/{id}` | Single fragrance detail | — |
| POST | `/fragrances/quiz/session/start` | Start a quiz session (seeds spanning olfactory families) | optional |
| POST | `/fragrances/quiz/session/{id}/answer` | Record one answer (in-memory) | optional |
| POST | `/fragrances/quiz/session/{id}/evaluate` | Compute confidence, decide if more questions are needed | optional |
| GET | `/fragrances/quiz/session/{id}/next-questions` | Next extension questions (uncertainty/diversity ranked) | optional |
| POST | `/fragrances/quiz/session/{id}/finalize` | Persist quiz ratings, mark quiz complete | legacy |
| POST | `/fragrances/quiz/session/{id}/guest-finalize` | Finalize a guest quiz (no DB write) | optional |
| POST | `/recommendations/guest` | Guest recommendations through the 3-state dispatcher | — |
| POST | `/recommendations/rate` | Save a single rating (1–10) | legacy |
| POST | `/recommendations/batch-rate` | Save many ratings at once | legacy |
| GET | `/recommendations/personalized` | Recommendations from a user's stored ratings | legacy |
| GET | `/users/profile` | Profile + rating count | legacy |
| POST | `/users/preferences` | Merge stored preferences | legacy |
| GET | `/health` | Health check incl. embedding-cache status | — |

---

## The ML bit

**What the embeddings are.** Fragrances that share notes and accords are linked into a symmetric Jaccard-similarity graph: an edge exists between two fragrances with the same primary accord whose note-Jaccard is > 0.2 (top-k 10 neighbors), and the accord signal is scaled into the input features with weight 0.2. A 2-layer GraphSAGE (64-d, seed 42, edge_dropout 0.1) is trained with an **anchored InfoNCE** contrastive loss — per-edge neighbor positives, per-edge negatives, plus a small off-diagonal Gram uniformity term that prevents embedding collapse. `all-MiniLM-L6-v2` text features (384-d, L2-normalized) are concatenated with the graph features, so each of the 4,559 catalog items ends with a 64-dimensional, L2-normalized vector encoding "who smells like me."

**Ratings are directional, not scalar.** A rating is not used as a raw 1–10 number; it is *centered on the neutral point* so it preserves direction:

| Rating | Weight `(rating − 5) / 5` | What it does |
|---|---|---|
| 10 | +1.0 | strongly liked — pulls the profile toward this item |
| 8 | +0.6 | liked |
| 5 | 0.0 | neutral — no directional signal |
| 3 | −0.4 | disliked — pushes the profile away |
| 1 | −1.0 | strongly disliked — pushes the profile away |

A purely neutral set (all 5s) carries no directional signal: `compute_user_vector` refuses to fabricate a preference and the dispatcher falls back to popularity.

**How they're used at serving time.** No model inference, no PyTorch in the API. The embeddings are precomputed and shipped as a `.npy` file. For a cold user:

1. Each rating becomes its signed weight `(rating − 5) / 5` (clamped to [−1, 1]); the weighted average of the rated items' embeddings becomes a **user vector** (L2-normalized). Items the user already rated are excluded from the results.
2. Cosine similarity (a NumPy dot product — identical to an inner product because every row is L2-normalized) ranks all catalog items against that vector — a **KNN** search.
3. The top matches are hydrated with catalog metadata and returned.

If the embedding cache can't load (e.g., NumPy missing), the dispatcher automatically falls back to popularity.

### How we know it works — offline intrinsic proxy (NOT user-validated)

This repository has **no real user-interaction history** (no user ratings, reviews, or observed behavior). To measure the embedding path without fabricating data, `backend/ml/eval/run_cold_start_eval.py` runs a **synthetic, content-based evaluation** (`backend/ml/eval/README-COLD-START.md`): for each `k ∈ {1,2,3,5}` it runs `N=300` seeded trials (seed 42), draws `k` items from a random same-family group the user is assumed to like, and ranks by our user vector vs. **popularity** and **random** baselines. A candidate counts as relevant iff a content oracle (same primary accord AND note-Jaccard > 0.20) says it overlaps the seeds. Metrics: P@5, P@10, Recall@10, NDCG@10, with bootstrap 95% CIs.

**These numbers measure item-recall ability against a content oracle — not user satisfaction.** We make no claim that real users have validated these recommendations.

Retrained snapshot `f9117664b8` (evaluation report: `backend/ml/eval/runs/`):

| k (seed items) | P@5 | P@10 | Recall@10 | NDCG@10 | win-rate vs popularity (R@10) |
|---|---|---|---|---|---|
| 1 | 0.3467 | 0.2383 | 0.6404 | 0.6597 | 0.9233 |
| 2 | 0.3553 | 0.2817 | 0.4058 | 0.4799 | 0.8167 |
| 3 | 0.4140 | 0.3377 | 0.3876 | 0.5193 | 0.9100 |
| 5 | 0.4860 | 0.3980 | 0.3217 | 0.5320 | 0.8133 |

Bootstrap CIs and the pre-fix baseline snapshot `699cf6fa30` (e.g. k=1 NDCG@10 0.4021 vs. retrained 0.6597) are in `backend/ml/eval/runs/*.md`. Recall@10 stays low because its denominator is the whole relevant pool of the accord family (often hundreds of items); what matters is how P@k and R@k respond to `k` and that the model beats both baselines on identical trials.

**Feature-source ablations & real-behaviour validation** — `backend/ml/eval/ABLATIONS.md` measures graph-only vs text-only vs full (accord+text) variants and a pure-content `content-itemknn` baseline, and reports a real-data run on the public **Atrafshan** per-user vote dataset (`backend/ml/eval/run_real_data_eval.py`, results in `backend/ml/eval/runs/real-data/`). Two findings change how to read the table above: (1) on the intrinsic content oracle a pure content profile beats every learned variant (win-rates 1–7%) because it ranks on the very features the oracle scores — so the injected table proves retrieval capability, not user preference; (2) on real observed votes, popularity beats thin-feature content matching by ~90% of trials, confirming the honest frontier is validating on a content-rich catalog with real votes, not more intrinsic proxies.

**Artifact validation** — `backend/app/data/metadata.json` records every check, all passing at export: exact `[4559×64]` float32 shape; 4,559 unique ids in catalog order; L2 norms exactly 1.0; no NaN/Inf; **0 rounded-duplicate rows** (the pre-fix artifact had 34); within-primary-accord median cosine 0.3846 vs cross-accord −0.0204 (structure, not collapse); 364 isolated nodes (7.98%, graph coverage); order-invariance |Δ| < 1e-3 passes; catalog SHA-256 `53ad1d50…af97f1` ties the artifact to its input data.

**Regenerating the embeddings.** The training code lives in `backend/train.py` and needs training-only dependencies:

```bash
cd backend
pip install -e ".[ml]"               # torch, sentence-transformers, pandas, ranx, ...
python train.py                      # defaults: 100 epochs, all-MiniLM-L6-v2, seed 42
python train.py --skip-text          # reuse cached text_embeddings.npy
```

`train.py` validates its outputs, writes `app/data/metadata.json` (training settings, validation results, Python/NumPy/torch/sentence-transformers versions), regenerates the SHA-256 tracker, and atomically replaces the artifacts. To re-snapshot and re-run the offline evaluation against a new artifact:

```powershell
python backend/ml/eval/run_cold_start_eval.py --seed 42 --trials 300 --artifacts backend/ml/eval/data/<run-dir>
```

CLI args: `--epochs` (default 100), `--text-model` (default `all-MiniLM-L6-v2`), `--skip-text` (reuse cached `text_embeddings.npy`). The first run downloads the MiniLM model (~90 MB).

---

## Project structure

```
start.ps1                     # one-command dev launcher (backend + frontend)
backend/
├── app/
│   ├── main.py               # FastAPI entry — mounts routers, /health, lifespan init
│   ├── config.py             # settings: DATABASE_URL, JWT_SECRET_KEY, CORS
│   ├── database.py           # sync SQLAlchemy engine + session (SQLite)
│   ├── models/models.py      # 2 tables: users, fragrance_ratings
│   ├── auth/
│   │   ├── auth.py           # legacy bcrypt + JWT (retired; read lazily, never required)
│   │   └── dependencies.py   # Bearer-token dependency (optional variant for quiz)
│   ├── routers/
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
    ├── families/[family]/page.tsx
    └── fragrances/[id]/page.tsx   # fragrance detail + rating
```

---

## Tests

```bash
cd backend
python -m pytest tests -q
```

The backend suite (`python -m pytest tests -q` — 35 tests) covers the dispatcher state transitions, user-vector + KNN behavior, feature-based scoring, catalog loading, the quiz flow, and the public `/health` check.

ML/training tests (`python -m pytest ml/tests -q` — 185 tests, needs `pip install -e ".[ml]"`) cover the training pipeline, embedding-validation gates, and the cold-start evaluator and its oracle. The evaluator is also isolated as pure functions so it runs without the app or a database.

---

## Notes / interview angles

- **Why 3 states?** Warmth is a gradient — unknown → quiz-cold → known. The earlier 5-state design added β-blends and diversity injection that complicated the code without defensible user value at this scale, so it was cut.
- **Why precomputed embeddings?** Cold-start recommendations don't change with every request — training once offline and serving a NumPy lookup makes the API fast, dependency-free (no PyTorch at runtime), and trivially reproducible via `train.py`.
- **Ratings are directional.** The user vector is built from centered weights `(rating − 5) / 5`, not raw the 1–10 value — a 10/10 and a 1/10 are opposites (pull *toward* / push *away*), and a neutral 5 contributes nothing. This makes cold-state personalization direction-aware with as little as one signal.
- **Evaluation honesty.** The only metrics we can produce without real users are offline, synthetic, content-oracle-based (see "How we know it works"). Those numbers compare retrieval capability against popularity/random baselines; they are **not** evidence of real-user satisfaction, and we say so in the docs.
- **Why no Docker?** The whole system runs on two processes (`uvicorn` + `next dev`), launched by a single `start.ps1`. Docker orchestration for one backend and one frontend was overhead, not value.
- **Own every line.** The codebase is intentionally small and fully understood — no framework boilerplate you can't explain.
- **Honest about the ML.** Embeddings give you "similar to what you rated"; once a user has enough ratings, interpretable feature overlap takes over. The system is honest about what each state can and can't do.