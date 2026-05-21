# Codebase Concerns

**Analysis Date:** 2026-05-21

## Tech Debt

### Missing Celery Worker App Crashes Worker Container

- **Issue:** `docker-compose.yml` references `celery_app.py` for the worker service, but `backend/app/celery_app.py` does not exist. The coverage HTML report at `backend/htmlcov/z_5f5a17c013354698_celery_app_py.html` confirms it once existed but was removed. The worker container loops on restart.
- **Files:** `docker-compose.yml` (worker service), `backend/app/celery_app.py` (missing)
- **Impact:** Worker container never starts. Async tasks (weekly refresh, email sending, recomputation) silently fail. The "weekly_refresh" Prefect flow in `ml/flows/weekly_refresh.py` has no working executor.
- **Fix approach:** Either restore `celery_app.py` with proper Celery app initialization, or remove the worker service from `docker-compose.yml` and document that async jobs are not currently supported.

### Dead Endpoints — `/fragrances/recommend/text` and `/fragrances/recommend/profile`

- **Issue:** The endpoints `recommend_by_text()` and `recommend_by_profile()` in `backend/app/routers/fragrances.py` were removed. The test file `backend/tests/test_recommendation_lifecycle.py` explicitly tests they return 404 (lines 41-65). Recommendation logic was migrated to `backend/app/routers/recommendations.py` but `/fragrances/recommend/text` and `/fragrances/recommend/profile` have no replacements.
- **Files:** `backend/app/routers/fragrances.py`, `backend/tests/test_recommendation_lifecycle.py`
- **Impact:** Any client (or frontend) that still calls these old endpoints will silently fail. The frontend `api.ts` does not call them, but any external integrations might.
- **Fix approach:** Remove dead route registrations or add explicit redirect responses from the old paths.

### `ml/training/` Directory Never Created

- **Issue:** `ml/README.md` documents `ml/training/train_graphsage.py` and `ml/training/evaluate.py` as existing paths, but the `ml/training/` directory does not exist. The entire training/evaluation pipeline documented there cannot run.
- **Files:** `ml/README.md`, `ml/training/` (missing)
- **Impact:** Training workflow is documented but unimplemented. The GraphSAGE model in `ml/models/graph_sage.py` has a `_train_embeddings()` method with hardcoded hyperparameters (120 epochs, 0.01 LR, 20 patience) — no ability to evaluate or iterate.
- **Fix approach:** Create the directory with the training scripts, or update documentation to match current state.

### Startup Warmup Commented Out

- **Issue:** In `backend/app/main.py` lines 58-59, the neural engine warmup and catalog preload are commented out:
  ```python
  # warmup_neural_engine()
  # asyncio.create_task(load_recommendation_catalog_async())
  ```
  The comment says "NO ML loading blocks startup - lazy loading enabled." However, this means every first request pays a cold-start penalty.
- **Files:** `backend/app/main.py` (lines 55-64)
- **Impact:** First request to `/recommendations/guest` triggers lazy warmup in the request path (line 204-206 of `recommendations.py`), causing 2-5 second latency on initial call.
- **Fix approach:** Re-enable background warmup via `asyncio.create_task()` at startup.

### Debug `print()` Statements in Production Code

- **Issue:** Multiple `print()` calls exist in production code paths instead of structured logging:
  - `backend/app/services/hybrid_search.py` lines 357, 360, 361, 423, 501
  - `backend/app/routers/recommendations.py` lines 31, 202
  - `backend/app/main.py` line 67
- **Files:** `backend/app/services/hybrid_search.py`, `backend/app/routers/recommendations.py`, `backend/app/main.py`
- **Impact:** Pollutes stdout, cannot be filtered or routed, may leak internal data in production logs.
- **Fix approach:** Replace all `print()` with `logger.info()` or `logger.debug()`.

### Duplicate Encryption Service Implementations

- **Issue:** Two separate PII encryption services exist:
  - `backend/app/auth/encryption.py` — `DataVault` class (Fernet, uses `settings.data_encryption_key`)
  - `backend/app/services/vault.py` — `VaultService` class (Fernet with PBKDF2 derivation)
  
  These serve the same purpose with different implementations. `DataVault` uses `settings.data_encryption_key` directly as a Fernet key; `VaultService` derives a key from `settings.data_encryption_key` using PBKDF2 with a hardcoded salt.
- **Files:** `backend/app/auth/encryption.py`, `backend/app/services/vault.py`
- **Impact:** Confusion about which service to use. `DataVault` is used in `auth/` and `supabase_auth.py`; `VaultService` appears to be unused by callers.
- **Fix approach:** Consolidate into a single encryption service. The `DataVault` approach is simpler and matches what `auth/` and `supabase_auth.py` use.

### `ruff: noqa` Disables All Linting on Hybrid Search

- **Issue:** `backend/app/services/hybrid_search.py` line 1 has `# ruff: noqa`, bypassing all linting. This file is the core recommendation engine — 590 lines of complex logic with no lint enforcement.
- **Files:** `backend/app/services/hybrid_search.py`
- **Impact:** Code quality issues in the most critical backend file are invisible to CI. Contains debug print statements, complex mutable state, and long functions.
- **Fix approach:** Remove `ruff: noqa` and fix lint violations incrementally.

### Version Inconsistency

- **Issue:** Three different version strings exist:
  - `backend/app/main.py` line 81: `version="0.0.1"` (FastAPI app metadata)
  - `backend/app/main.py` line 140: `"version": "0.1.0"` (root `/` endpoint)
  - `backend/app/main.py` line 149: `"version": "0.0.1"` (standalone `/version` endpoint)
- **Files:** `backend/app/main.py` (lines 81, 140, 149)
- **Impact:** Confuses API consumers, makes version-based debugging unreliable.
- **Fix approach:** Centralize version string in `config.py` and reference it everywhere.

### Missing `npm test` Script

- **Issue:** `Makefile` line 39 runs `cd frontend && npm test`, but `frontend/package.json` has no `test` script — only `test:e2e`, `test:e2e:ui`, `test:e2e:debug`, and `test:e2e:report`.
- **Files:** `Makefile` (line 39), `frontend/package.json`
- **Impact:** `make test-frontend` fails. CI/CD pipeline that runs frontend tests will break.
- **Fix approach:** Update Makefile to `npm run test:e2e` or add a `test` script to `package.json`.

### Mismatched Dependency Specifications

- **Issue:** `backend/pyproject.toml` and `backend/requirements.txt` define overlapping but inconsistent dependencies:
  - `celery>=5.3.6` exists in `requirements.txt` but not in `pyproject.toml`
  - `aiofiles`, `psutil`, `python-dotenv` in `pyproject.toml` but duplicated also in `requirements.txt`
  - `slowapi` pinned ranges differ
- **Files:** `backend/pyproject.toml`, `backend/requirements.txt`
- **Impact:** Confusion about which is the source of truth. Pip-install behavior differs based on which file is used.
- **Fix approach:** Remove `requirements.txt` and use `pyproject.toml` exclusively, or vice-versa.

## Known Bugs

### Frontend API Route Mismatch for Wishlist

- **Symptoms:** Frontend `api.ts` line 116 calls `POST /users/saved` for adding to wishlist. But the E2E tests in `fixtures.ts` mock `POST /api/user/wishlist/:id` — a different URL pattern. MSW handlers in `handlers.ts` mock `POST /api/user/wishlist/:id`. The actual backend endpoint is `POST /users/saved` (from `backend/app/routers/users.py` line 265).
- **Files:** `frontend/src/lib/api.ts` (line 116), `frontend/tests/fixtures.ts` (lines 146-163), `frontend/tests/mocks/handlers.ts` (lines 221-226), `backend/app/routers/users.py` (line 265)
- **Trigger:** Any E2E test or frontend code that uses the wishlist via different URL patterns will get inconsistent behavior.
- **Workaround:** Tests use mocks, so they pass independently. Integration tests would fail.

### `_normalize_id` Prefix Stripping Fragile

- **Symptoms:** `backend/app/routers/recommendations.py` line 77 strips `frag_syn_` and `frag_` prefixes from IDs. The `quiz.py` router (line 470) duplicates this stripping. Any new prefix added to the frontend will silently fail to match catalog IDs.
- **Files:** `backend/app/routers/recommendations.py` (line 77), `backend/app/routers/quiz.py` (line 470)
- **Trigger:** Adding a new prefix pattern in the frontend without updating both backend locations.
- **Workaround:** Centralize normalization into a shared utility function.

### Rate Limiter Not Test-Aware

- **Symptoms:** `backend/app/limiter.py` line 8 disables rate limiting when `pytest` is in `sys.modules`. However, this means rate-limited endpoints are never tested under realistic conditions.
- **Files:** `backend/app/limiter.py`
- **Trigger:** Rate limit bypass is global — not scoped to test clients.
- **Workaround:** Use dependency override for rate limiter in test fixtures instead of module-detection hack.

## Security Considerations

### Hardcoded Development Secrets in Docker Compose

- **Risk:** `docker-compose.yml` line 73 defaults `JWT_SECRET_KEY` to `dev_secret_key_change_in_production`. If a production deployment uses this default (e.g., by forgetting to override the env var), JWT tokens can be forged.
- **Files:** `docker-compose.yml` (line 73)
- **Current mitigation:** The environment variable has a `:-` default, so it only applies if not set.
- **Recommendations:** Add a startup check that refuses to start with the default dev key. Fail loudly if `JWT_SECRET_KEY` equals the known default.

### PII Encryption Silently Falls Back to Plaintext

- **Risk:** `backend/app/auth/encryption.py` lines 25-26: when Fernet is unavailable (missing `cryptography` package), `encrypt()` and `decrypt()` return the data unencrypted. No error is raised. PII stored in the database could be plaintext.
- **Files:** `backend/app/auth/encryption.py` (lines 25-26)
- **Current mitigation:** None — silent pass-through.
- **Recommendations:** Raise `RuntimeError` at startup if `cryptography` is not installed, or at least log a CRITICAL warning that encryption is disabled.

### Hardcoded Fallback Encryption Key and Salt

- **Risk:** `backend/app/services/vault.py` line 13 uses `"dev_fallback_key_change_in_production"` and line 16 uses hardcoded salt `b"scentrix_salt"` when `DATA_ENCRYPTION_KEY` is not set. These values are in source control, so anyone with repo access can decrypt PII.
- **Files:** `backend/app/services/vault.py` (lines 13, 16)
- **Current mitigation:** Only used if `DATA_ENCRYPTION_KEY` env var is missing.
- **Recommendations:** Raise an error at startup if `DATA_ENCRYPTION_KEY` is not set rather than falling back to hardcoded values.

### Supabase JWT Verification Bypassed

- **Risk:** `backend/app/services/supabase_auth.py` line 81 uses `jwt.get_unverified_claims(token)` to decode Supabase JWTs **without signature verification**. The comment says "We bypass signature verification since the secret is hidden by Supabase."
- **Files:** `backend/app/services/supabase_auth.py` (line 81)
- **Current mitigation:** None — any malformed JWT with matching claims is accepted.
- **Recommendations:** Fetch the Supabase JWKS keys and verify signatures properly. The Supabase JWT secret is available via `SUPABASE_JWT_SECRET` — use it.

### Email Hash Without Salt (Rainbow Table Susceptible)

- **Risk:** `backend/app/services/supabase_auth.py` line 100 and `backend/app/routers/auth.py` line 54 use `hashlib.sha256(email.lower().strip().encode()).hexdigest()` without salt. This allows rainbow table attacks to reverse email hashes.
- **Files:** `backend/app/services/supabase_auth.py` (line 100), `backend/app/routers/auth.py` (line 54)
- **Current mitigation:** Email is also stored encrypted, but the hash is used as a lookup key.
- **Recommendations:** Use a per-application salt with the hash, or use HMAC with a secret key.

### CORS Allows All Headers

- **Risk:** `backend/app/main.py` line 97 sets `allow_headers=["*"]`, which allows all custom headers in CORS requests.
- **Files:** `backend/app/main.py` (line 97)
- **Current mitigation:** `allow_origins` is limited to two known origins (localhost:3000).
- **Recommendations:** Restrict `allow_headers` to application-specific headers only.

### Frontend Token in Cookie Without HttpOnly

- **Risk:** `frontend/src/stores/app-store.ts` line 252 sets the auth cookie via `document.cookie` without `HttpOnly` flag. The frontend middleware reads this cookie for auth checking. Without `HttpOnly`, an XSS attack can steal the auth token.
- **Files:** `frontend/src/stores/app-store.ts` (line 252), `frontend/middleware.ts`
- **Current mitigation:** None by default — relies on no XSS vulnerabilities.
- **Recommendations:** Set auth cookies server-side (via API response headers) with `HttpOnly`, `Secure`, and `SameSite=Strict` flags. Use the client-side cookie only as a fallback.

## Performance Bottlenecks

### First Request Cold-Start Penalty

- **Problem:** Every first request to `/recommendations/guest` triggers lazy loading of embeddings and catalog data in the request path.
  - `backend/app/routers/recommendations.py` lines 204-206 trigger `warmup_neural_engine()` inline
  - `backend/app/services/hybrid_search.py` lines 30-102 load and normalize embeddings (~24K items with numpy ops) on first instantiation
- **Files:** `backend/app/routers/recommendations.py`, `backend/app/services/hybrid_search.py`
- **Cause:** Startup warmup was commented out in `main.py`.
- **Improvement path:** Re-enable background warmup via `asyncio.create_task()` and add a readiness probe that waits for warmup.

### Candidate Pool Sorting on Every Request

- **Problem:** `backend/app/services/hybrid_search.py` line 415 and 419 sort the full catalog by `rating_count` when the candidate pool is too small or too large. This is a redundant O(n log n) operation on every recommendation request.
- **Files:** `backend/app/services/hybrid_search.py` (lines 415, 419, 373-375)
- **Cause:** No pre-sorted index for popularity-based fallback.
- **Improvement path:** Pre-sort catalog once at load time and cache the sorted order.

### Redundant Catalog Lookups in Search

- **Problem:** `backend/app/routers/fragrances.py` `get_fragrance_detail()` calls `_catalog_filtered_rows()` up to three times in fallback paths (lines 552-557, 574-580, 634-639). Each call may re-parse the same data.
- **Files:** `backend/app/routers/fragrances.py` (the `get_fragrance_detail` function, lines 544-640)
- **Cause:** Fallback logic is layered rather than unified.
- **Improvement path:** Query the catalog once, cache the result, use a single fallback path.

## Fragile Areas

### Module-Level Global Caches

- **File:** `backend/app/services/catalog.py` — `_catalog_cache` (line 16), `_driver` (line 17), `_load_lock` (line 18)
- **File:** `backend/app/services/hybrid_search.py` — `_catalog_embeddings_cache` (line 31), `_is_hydrating` (line 32)
- **File:** `backend/app/services/quiz_store.py` — `_memory_store` (line 22), `_redis_client` (line 25)
- **File:** `backend/app/cache.py` — `RedisCache` instance at module level (line 47)
- **Why fragile:** Module-level mutable globals are:
  1. Not thread-safe in uvicorn with multiple workers
  2. Not reset between tests (test pollution)
  3. Cannot be dependency-injected for mocking
- **Safe modification:** Replace with FastAPI `app.state` or proper dependency injection. Wrap caches in singleton classes with clear lifecycle management.

### GraphSAGE Uses Random Node Split (Not Cold-Start Split)

- **File:** `ml/models/graph_sage.py` lines 116-165 — `_build_split_masks()` uses random shuffle of nodes, not cold-start split. This means the model may appear to perform well in evaluation because test nodes share edges with training nodes.
- **Why fragile:** The evaluation metrics (val_loss, test_loss) do not reflect real-world performance on new (cold-start) fragrances. Training is a reconstruction task, not a recommendation task.
- **Safe modification:** Implement a temporal or feature-based cold-start split for evaluation to match the product requirement.

### Bare `pass` Statements in Error Handlers

- **Files:**
  - `backend/app/auth/auth.py` line 133 — swallowing JWTError
  - `backend/app/services/supabase_auth.py` line 65 — swallowing JSON decode error
  - `backend/app/services/hybrid_search.py` lines 42, 275 — swallowing errors
  - `backend/app/sentry_config.py` lines 29, 36 — swallowing import errors
  - `backend/app/migrations/versions/003_fix_schema_pii_and_ratings.py` lines 76, 86, 115 — swallowing ALTER failures
- **Why fragile:** Errors are silently consumed, making debugging nearly impossible. A schema migration failing could leave the database in an inconsistent state.
- **Safe modification:** Log all exceptions at minimum. For migrations, raise on failure.

### Redis Connection Without Reconnection Logic

- **File:** `backend/app/cache.py` — `get_redis()` creates a connection once and reuses it. If Redis restarts or the connection drops, all subsequent operations silently fail (caught by blanket `except Exception`).
- **Why fragile:** Cache becomes a silent black hole. Reads return None, writes are lost. No health check, no retry, no circuit breaker.
- **Safe modification:** Add connection health checks on each `get()`/`set()` call with automatic reconnection.

### E2E Test Fixtures with Insecure Cookie and Hardcoded IDs

- **File:** `frontend/tests/fixtures.ts` — sets cookie with `httpOnly: false` (line 33), uses hardcoded JWT token format (line 14), hardcoded user IDs (line 16).
- **File:** `frontend/tests/mocks/handlers.ts` — hardcoded test password `TestPassword123!` (line 168).
- **Why fragile:** Tests pass in isolation but mask real auth flow issues. When the real auth flow changes (e.g., token format), E2E tests still pass with mocks but the app breaks.
- **Safe modification:** Use MSW for API mocking but validate token/cookie formats against production patterns. Move test constants to a shared config.

## Scaling Limits

### In-Memory Fallback Stores

- **Current capacity:** `backend/app/services/quiz_store.py` stores quiz sessions in `_memory_store` dict (unbounded) when Redis is down.
- **Limit:** Memory grows linearly with concurrent quiz sessions. No eviction policy beyond TTL (which is not enforced for in-memory).
- **Scaling path:** Make Redis a hard requirement for multi-instance deployments. Use sticky sessions as emergency fallback only.

### HybridRecommender Singleton Per Process

- **Current capacity:** Single `HybridRecommender` instance at module level (`backend/app/services/hybrid_search.py` line 590), loaded with ~24K embeddings in memory (~24K × 384 dims × 4 bytes ≈ 37 MB + overhead).
- **Limit:** With multiple uvicorn workers, each loads a full copy. Memory scales linearly with worker count.
- **Scaling path:** Use Redis/Valkey for shared embedding storage, or pre-compute and store in a dedicated service.

## Test Coverage Gaps

### Dead Endpoint Tests Mask the Issue

- **What's not tested:** Whether the old `/fragrances/recommend/text` and `/fragrances/recommend/profile` endpoints have replacements. The test (`test_recommendation_lifecycle.py` lines 41-65) verifies they return 404, but no test verifies the new recommendation pipeline end-to-end with a real Neo4j backend.
- **Files:** `backend/tests/test_recommendation_lifecycle.py`
- **Risk:** The recommendation pipeline could be completely broken without any test catching it (since tests use SQLite and mock backends).
- **Priority:** High

### No Integration Tests for ML Pipeline

- **What's not tested:** The GraphSAGE training → embedding generation → Pinecone upload pipeline has no integration tests. The graph validation tests (`ml/tests/test_graph.py`) test graph construction only.
- **Files:** `ml/tests/`
- **Risk:** A change to the graph construction (e.g., `_build_node_features()`) could silently change all embeddings, degrading recommendation quality with no test signal.
- **Priority:** Medium

### Encryption Service Not Unit-Tested

- **What's not tested:** `backend/app/auth/encryption.py` and `backend/app/services/vault.py` have no dedicated unit tests. The encrypt/decrypt round-trip and fallback paths are untested.
- **Files:** `backend/app/auth/encryption.py`, `backend/app/services/vault.py`
- **Risk:** A regression in encryption could silently expose PII or corrupt user data.
- **Priority:** High

---

*Concerns audit: 2026-05-21*
