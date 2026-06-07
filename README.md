# Scentrix

**Research Theme:** Graph-Based Preference Initialisation for Cold-Start Recommendation in Zero-Interaction Domains
**Primary Objective:** Demonstrate feasibility and operational deployability of graph-based preference initialization

## Project Context

Scentrix is a 3rd-year undergraduate research project for MEXT scholarship interviews (July 2026). Research theme: "Graph-Based Preference Initialisation for Cold-Start Recommendation in Zero-Interaction Domains." Started as a product-oriented perfume platform, pivoted to research. See [CHANGELOG.md](./CHANGELOG.md) for phase history and requirement traceability.

**Key constraints:** Local Docker only, no cloud costs. Precision@10 and NDCG@10 evaluation (Matsuo/Kashima lab standards). Popularity + Random baselines only (CF/MF meaningless for cold-start). Results presented as MEXT interview demo, not paper submission.

graph-based cold-start fragrance recommendation.

---

## Prerequisites

Before you begin, ensure you have the following installed:

| Tool | Version | Required for |
|------|---------|-------------|
| [Docker Desktop](https://docs.docker.com/get-docker/) | 24+ (with Compose v2 plugin) | Running all services (recommended path) |
| [Python](https://python.org) | >= 3.11 | Backend (non-Docker dev) |
| [Node.js](https://nodejs.org) | >= 20 | Frontend (non-Docker dev) |
| [npm](https://npmjs.com) | (ships with Node 20+) | Frontend dependency management |

**Docker Compose v2** (`docker compose` — space, not hyphen) is the plugin bundled with Docker Desktop. If you have the standalone `docker-compose` (v1, hyphenated), upgrade to v2.

**Windows users:** `make` is not available by default. Use the raw `docker compose` commands shown inline, or install Make via [Chocolatey](https://chocolatey.org/) (`choco install make`) / [winget](https://learn.microsoft.com/en-us/windows/package-manager/winget/) (`winget install GnuWin32.Make`).

## Quick Start

These seven steps take you from a fresh clone to a running application with data loaded.

```bash
# 1. Clone the repository
git clone <repo-url>
cd Scentrix

# 2. Configure environment (optional — defaults work out of the box)
cp .env.example .env

# 3. Start all Docker services (Postgres, Neo4j, Redis, backend, frontend)
docker compose up -d

# 4. Run database migrations
docker compose exec backend alembic upgrade head

# 5. Seed the database with fragrances and test data
docker compose exec backend python -m scripts.seed_data

# 6. Open the application
#    → http://localhost:3000

# 7. Complete the user journey (see § below)
```

> **Tip:** After step 3, check progress with `docker compose ps` or `docker compose logs -f`. All five containers must show `healthy` before proceeding.

### Quick reference (Makefile)

```bash
make help         # Show all available make targets
make up           # docker compose up -d
make down         # docker compose down
make logs         # docker compose logs -f
make migrate      # docker compose exec backend alembic upgrade head
make seed         # docker compose exec backend python -m scripts.seed_data
make test-backend # Run backend test suite (requires running system)
```

---

## User Journey

Once the app is running at `http://localhost:3000`, follow this flow to experience the full recommendation pipeline:

### 1. Register an account

- Open `http://localhost:3000/auth/register` (or click "Sign Up" from the landing page)
- Enter an email and password
- You will be logged in automatically after registration

### 2. Browse the fragrance catalog

- The landing/home page shows the fragrance catalog
- Browse through the list or use search to find specific fragrances
- Click on any card to see fragrance details (notes, accords, description)

### 3. Take the preference quiz

- Navigate to the quiz section (`/quiz` or from the nav menu)
- You will be shown a series of fragrances — rate each on a 1–10 scale
- The quiz adapts based on your responses (more items may be requested)
- After rating, **finalise your quiz session** to submit your preferences
- A success screen confirms your quiz is complete

### 4. View your recommendations

- Navigate to `/recommendations`
- The system has now moved from **State 0 (Anonymous / Popularity)** to **State 1 (Quiz User / GraphSAGE)**
- Recommendations are computed using your per-item ratings weighted by GraphSAGE embeddings (USER_VECTOR path)
- The UI shows your current recommendation state (0–4) via the StateIndicator

### 5. Rate individual fragrances (Star button)

- On any recommendation or catalog page, click the **Star** icon to rate a fragrance (1–5 stars)
- Each rating moves you closer to the next state:
  - **1–4 ratings → State 2 (Cold / Hybrid):** Blend of GraphSAGE + feature-based scoring
  - **5–19 ratings → State 3 (Warm / Feature-based):** Feature-based primary with GraphSAGE exploration
  - **20+ ratings → State 4 (Mature / Feature-based + diversity):** Feature-based with diversity injection

### 6. Check your profile

- Visit `/profile/history` to see your **Last Quiz Summary** card
- Shows total rated, average rating, top matches, and preferred notes/accords

### State reference

| State | Label | Ratings | Strategy |
|-------|-------|---------|----------|
| 0 | Anonymous | 0 | Popularity only |
| 1 | Quiz User | 0 (quiz completed) | GraphSAGE (USER_VECTOR) |
| 2 | Cold | 1–4 | Hybrid (GraphSAGE + Feature-based) |
| 3 | Warm | 5–19 | Feature-based primary |
| 4 | Mature | 20+ | Feature-based + diversity |

See [ARCHITECTURE-FREEZE.md](./ARCHITECTURE-FREEZE.md) for full dispatch details.

---

## what's the move?

hybrid research + engineering. the thesis: **cold-start preference initialization via direct user-vector from quiz ratings**. the original pipeline (confidence → seeds → centroid → GraphSAGE) discarded per-item rating information at every stage. the USER_VECTOR path (rating-weighted embedding sum → KNN) preserves the full signal and achieves +14.9% FH / +41.4% NDCG over centroid — simpler, faster, better.

## the numbers (canonical — Fix B applied)

⚠️ Phase 5.1 evaluation audit identified two flaws: (1) NDCG@10 was computed as RR@10, and (2) ground truth used note-Jaccard >0.20 (circular with the Jaccard graph). Fix A (true NDCG) and Fix B (brand+accord GT) have been applied. Values below are from the canonical reproducible pipeline: `SCENTRIX_EVAL_GT_MODE=brand_accord python -m ml.eval.pipeline --mode pure_cold --seed 42`.

| Model | Precision@10 | NDCG@10 | Recall@10 |
|---|---|---|---|
| GraphSAGE-Jaccard (pure_cold) | 0.0567 | **0.115** | 0.1396 |
| GraphSAGE-Embedding (pure_cold) | 0.0550 | **0.095** | 0.1075 |
| Feature-Only | 0.1825 | **0.399** | 0.4136 |
| Content-Only | 0.0193 | **0.047** | 0.0465 |
| Popularity | 0.0000 | **0.000** | 0.0000 |
| Random | 0.0007 | **0.001** | 0.0012 |

**bootstrap significance (n=10000, brand_accord GT):** Jaccard vs Embedding: p=0.008, d=0.11 (Jaccard leads by 1.21×). Jaccard vs Feature-Only: p=1.000, d=−0.96 (Feature-Only leads by 3.47×).

**headline:** Under non-circular brand+accord ground truth, Feature-Only (0.399 NDCG@10) dominates GraphSAGE-Jaccard (0.115) by 3.47×. GraphSAGE-Jaccard marginally outperforms GraphSAGE-Embedding (0.095) by 1.21× — structural independence helps modestly, but direct feature matching is substantially more predictive of brand+accord relevance on this dataset.

## key decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GraphSAGE on Neo4j | Graph-based preference init for cold-start — core hypothesis | Complete — Jaccard NDCG@10=0.115 vs Embedding 0.095 |
| Adaptive confidence quiz | Preference init without interaction history | Complete — analyzed; does not beat pure_cold (0.496 vs 0.504) |
| Popularity + Random baselines | Only honest cold-start baselines | Complete — NDCG@10=0.008, 0.021 |
| Precision@10 + NDCG@10 | Standard metrics for target labs | Complete — ranx-based, operational |
| Local Docker only | No cloud costs, sufficient | Confirmed |
| GraphSAGE as Preference Init Layer | Feature-Only beats GS at every coldness level by up to 3.5× | Architecture Freeze — GS alongside FB, never alone |
| USER_VECTOR over centroid | Preserves per-item signal, simpler, faster | Production — +14.9% FH / +41.4% NDCG, ~10× faster |

## the architecture

See [ARCHITECTURE-FREEZE.md](./ARCHITECTURE-FREEZE.md) for the canonical 5-state dispatch architecture.

## the product

5 Docker containers — Postgres 15, Neo4j 5, Redis 7, FastAPI backend, Next.js frontend. 5,000 quality-filtered items (from 22,740). 24 brands. 48 accords. 16,244 edges at threshold 0.20.

The recommendation flow: zero ratings → State 0 (popularity). Complete quiz → State 1 (GraphSAGE — user-vector from per-item ratings, centroid legacy fallback). Tap Star → State 2 (blended). 5 ratings → State 3 (feature-based). 20 → State 4 (feature-based + diversity).

API responses include `state` (0–4) and `state_label` to inform the frontend of the current dispatch state. Quiz endpoints include `POST /fragrances/quiz/session/{session_id}/guest-finalize` for guest persistence and `GET /recommendations/quiz-summary` for the Last Quiz Summary card on `/profile/history`.

### development commands

```bash
# start everything
docker compose up                                      # → http://localhost:3000

# run backend tests (requires running system)
make test-backend                                      # or: docker compose exec backend pytest
docker compose exec backend pytest tests/test_phase11_quiz.py  # single file

# run frontend checks (from frontend/)
npm run lint                                           # ESLint
npm run format                                         # Prettier
npm run type-check                                     # TypeScript (tsc --noEmit)
npm run build                                          # Next.js production build

# run e2e tests (Playwright, requires running system)
npm run test:e2e                                       # headless
npm run test:e2e:ui                                    # interactive UI mode
```

## the threshold

⚠️ "Group A NDCG" values from the original pipeline used circular jaccard GT. Under Fix B (brand_accord GT), absolute values are lower but the pattern — higher thresholds produce higher NDCG at the cost of coverage — is consistent. Threshold 0.20 remains the canonical choice, balancing coverage (99.2%) with reasonable NDCG.

| Threshold | Edges | Deg-0 | NDCG@10 | Precision@10 | Recall@10 |
|---|---|---|---|---|---|
| 0.10 | 21,452 | 12 | 0.082 | 0.043 | 0.102 |
| 0.15 | 20,124 | 27 | 0.084 | 0.045 | 0.102 |
| **0.20** | **16,244** | **84** | **0.113** | **0.054** | **0.135** |
| 0.25 | 10,821 | 204 | 0.168 | 0.082 | 0.189 |
| 0.30 | 6,341 | 369 | 0.233 | 0.108 | 0.253 |

## quiz_init (archived — superseded by USER_VECTOR)

The centroid-based quiz_init was evaluated under the original pipeline (circular jaccard GT, RR-as-NDCG). It does NOT reliably beat pure_cold (mean NDCG 0.496 vs 0.504, std 0.023, beats baseline 2/5 runs). Deemed not reproducible under corrected methodology. Superseded in production by USER_VECTOR (direct embedding lookup from per-item ratings). See `07_01-CONTEXT.md` for USER_VECTOR validation in its own evaluation context.

## coldness stratification

| Model | Level 0 (0 int.) | Level 1 (1-3) | Level 2 (4+) |
|---|---|---|---|
| GraphSAGE-Embedding | 0.095 | 0.071 | 0.131 |
| GraphSAGE-Jaccard | 0.115 | 0.081 | 0.152 |
| Feature-Only | 0.399 | 0.401 | 0.419 |
| Popularity | 0.000 | 0.001 | 0.001 |

Feature-Only leads all levels by a wide margin under brand_accord GT. Feature-Only and Popularity are near-constant across levels (feature-based signal does not degrade with coldness). GraphSAGE-Jaccard is monotonic across levels. GraphSAGE-Embedding non-monotonic (drops from 0.095 to 0.071 at Level 1 — low-pop connectivity weakness). Both GraphSAGE variants benefit from more interaction signal at Level 2, unlike Feature-Only which plateaus.

## roadmap

| Phase | Status | Focus |
|-------|--------|-------|
| 9 | ❌ Out of Scope | Graph Sync — irrelevant for static MEXT dataset |
| 10 | ⚠️ Reduced Scope | Auth & Ratings — guest persistence merged into Phase 11 |
| 11 | ✅ Complete | Quiz Flow Integration — 5 deliverables across Waves 1–3B |
| 12A | ✅ Complete | Structured Logging — correlation IDs, structured events across rec/quiz endpoints |
| 12B | ✅ Complete | Load Testing — Locust, 4 scenarios, 20 users/5-min ramp, all criteria PASS |
| 12C | ⏭️ Deferred | Performance Monitoring — `/metrics` endpoint with Prometheus |
| 12D | ❌ Dropped | Dashboards & Alerting — out of scope for MEXT demo |

See [CHANGELOG.md](./CHANGELOG.md) for full phase history, sub-phase details, and requirement→phase traceability.

### Phase 11 — Quiz Flow Integration (Complete)

Phase 11 delivered the end-to-end quiz→recommendation user experience across five deliverables:

| Wave | Deliverable | Summary |
|------|-------------|---------|
| 1 | Guest Quiz Persistence | `POST /fragrances/quiz/session/{session_id}/guest-finalize` — Redis session finalization for guests, DB upsert for authenticated users |
| 2 | StateIndicator + Cold→Warm UX | `StateIndicator.tsx` component, 5-state-aware header on `/recommendations`, `state`/`state_label` in API responses |
| 3A | Last Quiz Summary | `GET /recommendations/quiz-summary` endpoint, `/profile/history` page rewritten from mock timeline to real summary card |
| 3B | Quiz Flow Polish | Extension flow UI (evaluate→prompt→fetch more questions), loading overlay during finalization, post-completion success screen, user-visible error handling |

## run it yourself

```bash
python -m ml.eval.pipeline --mode pure_cold --seed 42  # canonical run
python -m ml.eval.run_bootstrap                           # bootstrap n=10000
python -m ml.eval.pipeline --mode quiz_sensitivity        # quiz sensitivity
python -m ml.eval.pipeline --mode stratification          # stratification grid
```
