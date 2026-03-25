# ScentScape Data Flow Analysis Report

**Generated:** March 25, 2026  
**Status:** CRITICAL FINDINGS - Multiple database and API integrations incomplete

---

## EXECUTIVE SUMMARY

The ScentScape architecture is **partially scaffolded** but **NOT production-ready**. All required databases (PostgreSQL, Neo4j, Redis, Pinecone) are configured in `docker-compose.yml` and `.env.example`, but **Neo4j integration is missing from the backend**, and most API endpoints are **placeholder TODOs**. The frontend is architecturally sound but depends on connecting to these missing endpoints.

---

## 1. DATABASE CONFIGURATION & STATUS

### ✅ PostgreSQL — CONFIGURED & READY

**Location:** [.env.example](.env.example)  
**Connection String:** `postgresql://scentscape:scentscape_password@localhost:5432/scentscape`

**Status:**
- ✅ Docker container defined in `docker-compose.yml`
- ✅ SQLAlchemy ORM models defined in [backend/app/models/models.py](backend/app/models/models.py)
- ✅ Database session factory configured in [backend/app/database.py](backend/app/database.py)
- ✅ Async session support initialized
- ✅ Database initialization on startup configured in [backend/app/main.py](backend/app/main.py)

**Tables Created:**
- `users` — User accounts with GDPR deletion support, email, hashed password, opt-in consent
- `fragrance_ratings` — User ratings across 5 dimensions (sweetness, woodiness, longevity, projection, freshness)
- `saved_fragrances` — User bookmarked/favorited fragrances
- `refresh_tokens` — JWT refresh token storage for session rotation

**Verdict:** PostgreSQL is **fully ready**. Tables will auto-create on first backend startup.

---

### ⚠️ Neo4j — CONFIGURED BUT NOT INTEGRATED

**Location:** [.env.example](.env.example)  
**Connection URI:** `neo4j://localhost:7687`  
**Credentials:** `neo4j / neo4j_password`

**Status:**
- ✅ Docker container defined in `docker-compose.yml` (neo4j:5-community)
- ✅ Connection parameters in [backend/app/config.py](backend/app/config.py)
- ⚠️ **NO Python Neo4j driver installed** (py2neo or neo4j-python-client)
- ⚠️ **NO Neo4j schema or node definitions**
- ⚠️ **NO queries implemented** — 6 TODOs in [backend/app/routers/fragrances.py](backend/app/routers/fragrances.py)

**Expected Nodes (from CLAUDE.md architecture):**
- `Fragrance` — 1,000+ fragrances from Fragrantica
- `Note` — 200+ fragrance notes (top/middle/base)
- `Accord` — 50+ accords (woody, citrus, floral, etc.)
- `Brand` — Brand entities
- `UserProfile` — User embedding vectors

**Expected Edges:**
- `HAS_NOTE` — Fragrance has note with intensity
- `BELONGS_TO_ACCORD` — Note belongs to accord
- `MADE_BY` — Fragrance made by brand
- `CO_RATED_WITH` — User co-rated fragrances
- `SIMILAR_TO` — Fragrance similarity

**Seed Data:** [ml/data/seed_fragrances.json](ml/data/seed_fragrances.json) contains 4 sample fragrances (Sauvage, Bleu de Chanel, Acqua di Parma, Creed Aventus) with notes and accords.

**Verdict:** Neo4j is **NOT integrated**. The container will run, but the backend cannot query it. This is the **CRITICAL BLOCKER** for fragrance search and recommendations.

---

### ⚠️ Redis — CONFIGURED BUT NOT USED

**Location:** [.env.example](.env.example)  
**Connection URL:** `redis://localhost:6379/0`

**Status:**
- ✅ Docker container defined
- ⚠️ **Not connected in backend** — No Redis client setup
- ⚠️ In-memory job cache used instead (see line 32 in [backend/app/routers/fragrances.py](backend/app/routers/fragrances.py)): `recommendation_jobs = {}`

**Intended Use:**
- Recommendation result caching (24h TTL per user)
- Celery broker for async tasks
- Session token blacklist

**Verdict:** Redis container will start, but backend ignores it. Recommendations will NOT persist across restarts.

---

### ⚠️ Pinecone — NOT INTEGRATED

**Location:** [.env.example](.env.example)  
**API Key:** `PINECONE_API_KEY` (placeholder)  
**Index:** `scentscape-fragrances` (128-dim, cosine metric)

**Status:**
- ✅ Credentials in config
- ❌ No Pinecone client in backend
- ❌ No embedding generation pipeline
- ❌ No vector similarity search

**Intended Use:**
- Store 128-dim GraphSAGE fragrance embeddings
- Fast ANN (Approximate Nearest Neighbor) lookup for recommendations

**Verdict:** Not integrated. Would require ML pipeline (Phase 3) to work.

---

## 2. BACKEND API ENDPOINTS

**API Base:** `http://localhost:8000`  
**Prefix:** `/api/v1` (in config but not used in routers)  
**Auth:** JWT Bearer token (HS256)

### ✅ IMPLEMENTED ENDPOINTS

#### Health & Info (Working)
| Method | Endpoint | Status | Implementation |
|--------|----------|--------|-----------------|
| GET | `/health` | ✅ | [backend/app/main.py](backend/app/main.py#L66) — Returns `{"status": "ok"}` |
| GET | `/` | ✅ | [backend/app/main.py](backend/app/main.py#L71) — Root info endpoint |
| GET | `/version` | ✅ | [backend/app/main.py](backend/app/main.py#L77) — Returns version "0.1.0" |

#### Authentication (Partially Implemented)
| Method | Endpoint | Status | Notes |
|--------|----------|--------|-------|
| POST | `/auth/register` | ⚠️ | [backend/app/routers/auth.py](backend/app/routers/auth.py#L29) — Implemented. Returns JWT tokens. |
| POST | `/auth/login` | ⚠️ | Partially implemented (check file for completion) |
| POST | `/auth/refresh` | ⚠️ | TODO: Implement token refresh |
| POST | `/auth/logout` | ⚠️ | TODO: Implement logout |

---

### ❌ NOT IMPLEMENTED ENDPOINTS (TODOs)

#### Fragrance Operations
| Method | Endpoint | Implementation | Blocker |
|--------|----------|-----------------|---------|
| GET | `/fragrances/{fragrance_id}` | [backend/app/routers/fragrances.py#L39](backend/app/routers/fragrances.py#L39) — Returns 404 | Needs Neo4j query |
| GET | `/fragrances/search` | [backend/app/routers/fragrances.py#L66](backend/app/routers/fragrances.py#L66) — Returns empty list | Needs Neo4j FT search |
| GET | `/fragrances/family/{family}` | TODO | Neo4j + Pinecone similarity |

#### Recommendation (Async)
| Method | Endpoint | Implementation | Blocker |
|--------|----------|-----------------|---------|
| POST | `/fragrances/recommend/text` | [backend/app/routers/fragrances.py#L101](backend/app/routers/fragrances.py#L101) — Creates job, no processing | Needs Celery + Sentence-BERT |
| GET | `/fragrances/recommend/{job_id}` | Polls in-memory cache | No Redis persistence |
| POST | `/fragrances/recommend/profile` | [backend/app/routers/fragrances.py#L150](backend/app/routers/fragrances.py#L150) — TODO | Needs user embedding + BPR |

#### User Profile
| Method | Endpoint | Implementation | Status |
|--------|----------|-----------------|--------|
| GET | `/users/profile` | [backend/app/routers/users.py#L27](backend/app/routers/users.py#L27) — Queries PostgreSQL | ✅ |
| POST | `/users/ratings` | [backend/app/routers/users.py#L51](backend/app/routers/users.py#L51) — Creates/updates rating | ✅ |
| GET | `/users/ratings` | TODO | Query PostgreSQL fragrance_ratings |
| POST | `/users/saved` | TODO | Create SavedFragrance |
| DELETE | `/users/data` | TODO | GDPR deletion endpoint |

---

## 3. FRONTEND DATA ACCESS

### API Integration

**Client Setup:** [frontend/src/lib/api-client.ts](frontend/src/lib/api-client.ts)
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
```

**State Management:** [frontend/src/stores/app-store.ts](frontend/src/stores/app-store.ts) (Zustand)
- Quiz state management ✅
- User preferences (gender-neutral, family filters, longevity) ✅
- Recommendations storage ✅
- Wishlist state ✅
- Auth token persistence (localStorage) ✅

**React Query Hooks:** [frontend/src/lib/hooks.ts](frontend/src/lib/hooks.ts)

| Hook | Endpoint | Status | Issue |
|------|----------|--------|-------|
| `useFragrances(family?)` | GET `/fragrances?family=X` | ⚠️ | Backend returns empty |
| `useFragrance(id)` | GET `/fragrances/{id}` | ❌ | Backend returns 404 |
| `useFragrancesByFamily(family)` | GET `/fragrances/family/{family}` | ❌ | Not implemented |
| `useStartQuiz()` | POST `/quiz/start` | ❌ | Endpoint missing |
| `useSubmitQuizAnswer()` | POST `/quiz/answer` | ❌ | Endpoint missing |
| `useCompleteQuiz()` | POST `/quiz/{quiz_id}/complete` | ❌ | Endpoint missing |
| `useRecommendations()` | GET `/recommendations` | ❌ | Endpoint missing |

### Frontend Routes

**Configured Routes:** [frontend/src/app/](frontend/src/app/)
- `/` — Home page (Hero, How It Works, Social Proof)
- `/onboarding/quiz` — Quiz flow (10-15 reference fragrances)
- `/families/[family]` — Fragrance by family (tries to call `/fragrances/family/{family}`)
- `/recommendations` — Results page (tries to call `/recommendations/*`)
- `/profile` — User profile (auth required)

**Current State:** Pages exist but API calls will fail because endpoints are not implemented.

---

## 4. AUTHENTICATION & AUTH STATE MANAGEMENT

### ✅ Authentication Implemented

**JWT Flow:**
1. User registers: `POST /auth/register` → Returns access & refresh tokens
2. Token stored in `localStorage.auth_token` (frontend)
3. Axios interceptor auto-adds: `Authorization: Bearer {token}` to all requests
4. 401 logout redirect on token expiry

**Backend Auth:** [backend/app/auth/auth.py](backend/app/auth/auth.py)
- Password hashing: bcrypt ✅
- Token generation: PyJWT ✅
- Token verification: ✅
- Algorithms: HS256 ✅

**Expiration:**
- Access token: 15 minutes (default)
- Refresh token: 7 days
- Refresh token blacklist: Needs implementation

**Frontend Auth State:** [frontend/src/stores/app-store.ts](frontend/src/stores/app-store.ts)
- `isAuthenticated` boolean ✅
- `authToken` string ✅
- `setAuthToken()` method ✅
- `logout()` method ✅

### ⚠️ Not Yet Implemented
- GDPR data deletion endpoint
- Refresh token revocation
- User profile retrieval after login
- Consent tracking for ML training

---

## 5. DATA TYPE: MOCK VS. REAL DATABASE

### Current State: **HYBRID — Mostly Mock**

| Data Source | Type | Status |
|-------------|------|--------|
| User accounts | Real PostgreSQL | Container ready, code ready |
| User ratings | Real PostgreSQL | Container ready, code ready |
| Fragrances | Mock (JSON seed) | Using [ml/data/seed_fragrances.json](ml/data/seed_fragrances.json) (4 samples) |
| Notes/Accords | Mock (in JSON) | Not in database yet |
| Notes graph edges | None | Not implemented |
| Recommendations | In-memory cache (ephemeral) | [backend/app/routers/fragrances.py#L32](backend/app/routers/fragrances.py#L32): `recommendation_jobs = {}` |
| Embeddings | None | Not generated |

### Seed Data Sample
[ml/data/seed_fragrances.json](ml/data/seed_fragrances.json):
```json
{
  "id": "frag_001",
  "name": "Sauvage",
  "brand": "Dior",
  "year": 2015,
  "top_notes": ["Bergamot", "Pepper", "Ambrette"],
  "middle_notes": ["Ambroxan", "Cedar"],
  "base_notes": ["Cedar", "Ambroxan"],
  "accords": ["Aromatic", "Spicy", "Woody"]
}
```

**Verdict:** Fragrances are **NOT in any database** — they're JSON only. Neo4j needs to be populated with this data.

---

## 6. MISSING CONNECTIONS (CRITICAL)

### 🔴 CRITICAL BLOCKERS

1. **Neo4j Driver Not Installed**
   - Required package: `neo4j-python-client` or `py2neo`
   - Impact: Cannot query fragrance graph, which breaks all search/recommendation features
   - Fix: `pip install neo4j` + implement queries in routers

2. **No Neo4j Schema or Data**
   - Seed JSON exists but not loaded into Neo4j
   - Need: Cypher script or init script to create nodes + edges
   - Impact: Database will be empty even if driver is installed

3. **No Celery Integration**
   - [backend/app/celery_app.py](backend/app/celery_app.py) exists but not configured/used
   - Recommendation endpoint creates job but never processes it
   - Impact: Text-to-fragrance recommendations always timeout or fail

4. **No Sentence-BERT Encoder**
   - Required for text-based recommendations
   - Model: `all-MiniLM-L6-v2` mentioned in CLAUDE.md
   - Impact: Cannot encode user natural language descriptions

5. **No GraphSAGE or Embeddings**
   - No embedding generation pipeline (Phase 3 responsibility)
   - Pinecone index not populated
   - Impact: Similarity search cannot work

6. **No Redis Client**
   - Recommendation jobs use in-memory dict instead of Redis
   - Impact: Jobs lost on restart; no cross-process caching

---

## 7. VERIFICATION CHECKLIST

| Item | Status | Evidence |
|------|--------|----------|
| PostgreSQL configured | ✅ | docker-compose.yml, config.py, database.py |
| PostgreSQL tables defined | ✅ | models.py (users, fragrance_ratings, saved_fragrances, refresh_tokens) |
| PostgreSQL async session | ✅ | database.py, FastAPI lifespan hook |
| Neo4j configured | ✅ | .env.example, config.py, docker-compose.yml |
| Neo4j driver installed | ❌ | Not in backend/pyproject.toml |
| Neo4j schema defined | ❌ | No Cypher scripts |
| Neo4j seed data loaded | ❌ | Seed JSON exists but not ingested |
| Redis configured | ✅ | .env.example, docker-compose.yml |
| Redis client installed | ❌ | Not in pyproject.toml |
| Pinecone configured | ✅ | .env.example, config.py |
| Pinecone client installed | ❌ | Not in pyproject.toml |
| FastAPI routes defined | ⚠️ | 3 routers: auth.py, fragrances.py, users.py (but mostly TODOs) |
| Health check endpoint | ✅ | [backend/app/main.py#L66](backend/app/main.py#L66) |
| Auth register endpoint | ✅ | [backend/app/routers/auth.py#L29](backend/app/routers/auth.py#L29) |
| Fragrance search endpoint | ❌ | Returns empty list, needs Neo4j |
| Recommendation endpoint | ⚠️ | Creates job but never processes |
| Frontend hooks configured | ✅ | [frontend/src/lib/hooks.ts](frontend/src/lib/hooks.ts) |
| Frontend state management | ✅ | [frontend/src/stores/app-store.ts](frontend/src/stores/app-store.ts) (Zustand) |
| Frontend API client | ✅ | [frontend/src/lib/api-client.ts](frontend/src/lib/api-client.ts) (Axios, JWT interceptor) |
| Seed fragrances JSON | ✅ | [ml/data/seed_fragrances.json](ml/data/seed_fragrances.json) (4 samples) |

---

## 8. RECOMMENDATIONS FOR IMMEDIATE NEXT STEPS

### Phase 2.1 (Backend Refinement) — Do Before Phase 3
1. **Install Neo4j driver:** `pip install neo4j`
2. **Create Neo4j initialization script:** Use Cypher to create schema and ingest seed_fragrances.json
3. **Implement fragrance.py queries:** 
   - `get_fragrance_by_id()` — Neo4j MATCH query
   - `search_fragrances()` — Full-text or Cypher FILTER
4. **Implement Redis client:** Use `redis-py` for caching
5. **Configure Celery:** Set up task queues for async recommendations
6. **Fix `/quiz/` endpoints:** Currently missing entirely

### Phase 3 (ML Pipeline)
1. Build GraphSAGE training pipeline (PyTorch Geometric)
2. Generate and upload embeddings to Pinecone
3. Implement Sentence-BERT text encoder
4. Hook async recommendation Celery task

---

## 9. ENVIRONMENT CONFIGURATION

### `.env.example` Status: ✅ COMPLETE
All required keys documented:
```
DATABASE_URL
NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
REDIS_URL
PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME
JWT_SECRET_KEY
SENTRY_DSN
CLOUDFLARE_R2_* (object storage)
NEXT_PUBLIC_API_URL
GENDER_NEUTRAL_RECOMMENDATIONS
```

### Current Status: ⚠️ NO .env FILE IN REPO
- Only `.env.example` present (correct for security)
- Users must create `.env` locally before running `docker-compose up`
- Docker-compose sets defaults if .env not present

---

## FINAL ASSESSMENT

| Layer | Readiness | Details |
|-------|-----------|---------|
| **Infrastructure** | 🟢 60% | PostgreSQL ready. Neo4j/Redis/Pinecone containers defined but not connected in code. |
| **Backend API** | 🟡 30% | FastAPI scaffold done. Auth working. Fragrance/recommendation endpoints are PLACEHOLDERs. |
| **Frontend** | 🟢 70% | Routes exist, state management solid, API client configured. Can't fetch data because backend is incomplete. |
| **Database** | 🔴 10% | PostgreSQL ready. Neo4j not integrated. No real fragrance data in any database. |
| **ML Pipeline** | 🔴 0% | Not started (Phase 3). No embeddings, no recommendations, no Celery. |
| **Overall** | 🔴 30% | **Not production-ready. Blocker: No Neo4j integration.** |

---

## CONCLUSION

**Current State:** The project has good scaffolding but **critical integrations are missing**. The databases are configured but not connected to the code. The API endpoints return placeholders. The frontend is ready to consume data but has nothing to fetch.

**Next Action:** Complete Phase 2 backend work before proceeding to Phase 3. Focus on:
1. Neo4j driver + schema + seed data ingestion
2. Fragrance query implementation
3. Redux/quiz endpoints
4. Celery task system

Then Phase 3 can build the ML pipeline on top of working database APIs.
