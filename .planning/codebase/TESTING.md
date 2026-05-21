# Testing Patterns

**Analysis Date:** 2026-05-21

## Test Framework Overview

The codebase has three separate test suites across three services:

| Suite | Framework | Location | Command |
|-------|-----------|----------|---------|
| Backend (Python) | pytest 7.4+ | `backend/tests/` | `pytest --cov=app` |
| Frontend E2E (TS) | Playwright 1.48+ | `frontend/tests/` | `npm run test:e2e` |
| ML (Python) | pytest | `ml/tests/` | `python -m ml.tests.<module>` |

---

## Backend Testing (pytest)

### Runner

**Framework:** pytest 7.4.3+
**Config:** `backend/pyproject.toml` under `[tool.pytest.ini_options]`
```ini
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "--cov=app --cov-report=html --cov-report=term-missing"
```

**Dependencies:** `pytest-asyncio`, `pytest-cov`, `httpx` (for async test client)

**Run Commands:**
```bash
pytest                              # Run all tests
pytest --cov=app --cov-report=html  # Run with coverage
pytest -xvs                         # Stop on first fail, verbose, no capture
pytest tests/test_auth.py           # Run specific file
```

### Test File Organization

**Location:** `backend/tests/` — separate directory from source (not co-located)

**Naming:** `test_<module>.py` — e.g., `test_auth.py`, `test_health.py`, `test_adaptive_quiz.py`

**Files:**
```
backend/tests/
├── __init__.py
├── conftest.py           # Fixtures: DB setup, HTTP client, session override
├── test_health.py        # Smoke tests (sync TestClient)
├── test_auth.py          # Auth flow: register, login, token, current user
├── test_adaptive_quiz.py # Quiz lifecycle: start, answer, evaluate, next, ownership
├── test_integration.py   # Cross-service integration tests
├── test_recommendation_lifecycle.py  # Recommendation pipeline tests
└── benchmark_sla.py      # SLA/performance benchmarks (not pytest)
```

### Test Structure

**Suite Organization:**

Sync tests (`test_health.py`) use `TestClient`:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "data": {"status": "ok"}}
```

Async tests (`test_auth.py`, `test_adaptive_quiz.py`) use `pytest.mark.asyncio`:
```python
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio  # Module-level mark

async def test_register_user(client: AsyncClient, db_session: AsyncSession):
    response = await client.post("/auth/register", json={...})
    assert response.status_code == 201
```

### Conftest Fixtures

File: `backend/tests/conftest.py`

**Session-level fixtures:**
- `event_loop` — creates event loop for the test session
- `setup_test_db` — creates in-memory SQLite database, creates/drops all tables

**Test-level fixtures:**
- `db_session` — provides an async SQLAlchemy session per test
- `client` — provides `httpx.AsyncClient` with FastAPI app using `ASGITransport`, overrides `get_session` dependency

**Test DB:**
- Uses SQLite in-memory: `sqlite+aiosqlite:///:memory:`
- Separate engine from production
- `check_same_thread=False` for async compatibility

```python
@asynccontextmanager
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_session():
        yield db_session
    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

### Mocking

**Framework:** `pytest.MonkeyPatch` for function-level mocking

**Patterns:**

1. **MonkeyPatch for catalog loading:**
```python
async def test_quiz_start_submit_and_evaluate_flow(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(quiz_router, "load_recommendation_catalog", lambda: _sample_catalog())
```

2. **In-memory dict stores for services:**
```python
store: dict[str, dict] = {}

async def fake_create_quiz_session(*, session_id: str, payload: dict):
    store[session_id] = payload

monkeypatch.setattr(quiz_router, "create_quiz_session", fake_create_quiz_session)
```

3. **No external mocking library** (no pytest-mock, no unittest.mock) — all mocking uses `monkeypatch` with hand-written fake functions

**What to Mock:**
- External services (Neo4j, Pinecone, Redis)
- Catalog loading functions (to return controlled sample data)
- Quiz session storage (in-memory dicts instead of Redis)
- Authentication dependencies

**What NOT to Mock:**
- FastAPI app itself (test via `TestClient` or `AsyncClient`)
- SQLAlchemy ORM models (use real in-memory SQLite)
- Pydantic schema validation
- Business logic and filtering functions

### Fixtures and Factories

**Test Data:**

Helper functions defined inline in test files — no centralized factories:

From `test_adaptive_quiz.py`:
```python
def _sample_catalog() -> list[dict]:
    return [
        {
            "id": "frag_001",
            "name": "Citrus Dawn",
            "brand": "Brand A",
            "top_notes": ["Bergamot", "Lemon"],
            "accords": ["Citrus", "Fresh"],
            "review_count": 120,
            "view_count": 9000,
            "popularity_score": 74,
        },
        # ... 9 more fragrances
    ]
```

From `test_auth.py` (inline auth helpers):
```python
async def _register_and_login(client: AsyncClient) -> tuple[dict[str, str], int]:
    email = f"adaptive_{uuid4().hex[:8]}@example.com"
    password = "SecurePass123!"
    register = await client.post("/auth/register", json={...})
    login = await client.post("/auth/login", json={...})
    ...
    return headers, user_id
```

**Location:** Helper functions are co-located in test files rather than shared across files.

### Coverage

**Requirements:** Code coverage is collected but no minimum threshold is enforced.

**View Coverage:**
```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```
Coverage HTML report goes to `backend/htmlcov/`.

### Test Types

**Smoke Tests** (`test_health.py`):
- Synchronous, no DB required
- Verify endpoints respond (health, root, version)
- Use FastAPI `TestClient` (synchronous)

**Unit/Feature Tests** (`test_auth.py`, `test_adaptive_quiz.py`):
- Async, DB-dependent
- Test full endpoint flows end-to-end via HTTP client
- Register → Login → Authenticated request cycle

**Integration Tests** (`test_integration.py`):
- Cross-service coordination
- Likely tests DB + Redis + Neo4j interaction paths

**SLA Benchmarks** (`benchmark_sla.py`):
- Not pytest-based
- Performance timing measurements

### Common Patterns

**Async Testing Pattern:**
```python
pytestmark = pytest.mark.asyncio

async def test_register_success(client: AsyncClient, db_session: AsyncSession):
    response = await client.post("/auth/register", json={...})
    assert response.status_code == 201
    data = response.json()["data"]
    assert "access_token" in data
```

**Error Testing Pattern:**
```python
async def test_register_duplicate_user(client: AsyncClient):
    await client.post("/auth/register", json=payload)
    response2 = await client.post("/auth/register", json=payload)
    assert response2.status_code == 409
    assert response2.json()["message"] == "Email already registered"
```

**Ownership Enforcement Pattern:**
```python
async def test_quiz_session_ownership_enforced(client, monkeypatch):
    owner_headers, _ = await _register_and_login(client)
    other_headers, _ = await _register_and_login(client)
    # ... setup fake session belonging to owner
    forbidden = await client.post(
        "/fragrances/quiz/session/qz_owner/answer",
        json={...},
        headers=other_headers,
    )
    assert forbidden.status_code == 403
```

**DB Verification Pattern:**
```python
import hashlib
email_hash = hashlib.sha256("test@example.com".lower().strip().encode()).hexdigest()
result = await db_session.execute(select(User).where(User.email_hash == email_hash))
user = result.scalar_one()
assert user is not None
assert verify_password("SecurePassword123!", user.hashed_password)
```

---

## Frontend Testing (Playwright E2E)

### Runner

**Framework:** Playwright 1.48+
**Config:** `frontend/playwright.config.ts`

**Run Commands:**
```bash
npx playwright test                     # Run all E2E tests
npx playwright test --debug             # Debug mode
npx playwright test --ui                # UI mode
npx playwright show-report              # View HTML report
npx playwright test --update-snapshots  # Update visual baselines
```

**Config Highlights:**
- `testDir: './tests'`
- `fullyParallel: true`
- `retries: 2` on CI, `0` locally
- `workers: 1` on CI
- `reporter: 'html'`
- `baseURL: 'http://localhost:3000'`
- `trace: 'on-first-retry'`
- `screenshot: 'only-on-failure'`

**Browser Matrix** (5 projects):
- Chromium (Desktop)
- Firefox (Desktop)
- WebKit (Desktop)
- Mobile Chrome (Pixel 5)
- Mobile Safari (iPhone 12)

**WebServer:** Automatically starts `npm run dev` before tests
```ts
webServer: {
  command: 'npm run dev',
  url: 'http://localhost:3000',
  reuseExistingServer: !process.env.CI,
}
```

### Test File Organization

**Location:** `frontend/tests/`
```
frontend/tests/
├── fixtures.ts                       # Custom test fixtures
├── mocks/
│   └── handlers.ts                   # Mock data + MSW handlers
├── e2e/
│   ├── main-flows.spec.ts            # Core UX contract tests
│   ├── authenticated-flows.spec.ts   # Auth-gated flow tests
│   └── api-integration.spec.ts       # Mocked API tests
├── visual-regression.spec.ts         # Visual baseline snapshots
├── visual-regression.spec.ts-snapshots/  # PNG baselines
├── E2E_TEST_GUIDE.md                 # Test documentation
```

**Naming:** `*.spec.ts` pattern for test files.

### Custom Fixtures

File: `frontend/tests/fixtures.ts`

**`authenticatedPage`** — Pre-sets auth state via `localStorage` and cookies:
```typescript
await context.addInitScript(({ t, u }) => {
  localStorage.setItem('auth_token', t);
  localStorage.setItem('user_id', u);
  localStorage.setItem('scentrix_cookie_consent', JSON.stringify({ state: 'accepted', ... }));
}, { t: token, u: userId });
```

**`apiMockedPage`** — Intercepts all API calls with mock responses via `page.route()`:
```typescript
await page.route('**/api/fragrances', (route) => {
  route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockFragrances) });
});
```

### Mocking

**Framework:** Two approaches:
1. **Playwright route interception** (primary) — `page.route('**/api/*', handler)` in `fixtures.ts`
2. **MSW** (available but not actively used) — `msw` package in devDependencies, handlers defined in `tests/mocks/handlers.ts`

**Mock Data:** Defined in `frontend/tests/mocks/handlers.ts`:
- `mockFragrances` — 3 sample fragrances
- `mockUser` — test user with preferences/wishlist
- `mockRecommendations` — 3 recommendations with match scores

**What to Mock:**
- All API endpoints (fragrances, auth, profile, recommendations, wishlist, quiz, families)
- Auth state (JWT tokens, user cookies)
- Cookie consent state

**What NOT to Mock:**
- UI rendering
- Navigation
- Form validation (client-side)
- Middleware redirects

### Visual Regression

File: `frontend/tests/visual-regression.spec.ts`

**Coverage:** 11 pages × 3 breakpoints = 33 snapshots (some pages share snapshots for 30 total)

**Breakpoints:**
- Desktop: 1280×720
- Tablet: 768×1024
- Mobile: 375×812

**Configuration:**
```typescript
const fullSnapshotName = `${snapshotName}-${breakpoint}.png`;
await expect(page).toHaveScreenshot(fullSnapshotName, {
  maxDiffPixels: 100,
  threshold: 0.2,
});
```

**Update baselines:** `npx playwright test tests/visual-regression.spec.ts --update-snapshots`

### Test Patterns (Main Flows)

File: `frontend/tests/e2e/main-flows.spec.ts`

**Page Object pattern not used** — tests use direct Playwright locators instead

**Patterns:**
```typescript
import { test, expect } from '../fixtures';

async function acceptCookiesIfVisible(page: Page) {
  const acceptBtn = page.locator('#cookie-accept-all');
  if (await acceptBtn.isVisible().catch(() => false)) {
    await acceptBtn.click();
  }
}

test.describe('Main Flows (Current UX Contract)', () => {
  test('home page renders hero and primary CTAs', async ({ page }) => {
    await page.goto('/');
    await acceptCookiesIfVisible(page);
    await expect(page.getByRole('heading', { name: /Discover Your Perfect Scent/i })).toBeVisible();
  });

  test('profile route enforces authentication guard', async ({ page }) => {
    await page.goto('/profile');
    await page.waitForTimeout(1200);
    if (page.url().includes('/auth/login')) {
      await expect(page).toHaveURL(/\/auth\/login/);
      return;
    }
    await expect(page.getByRole('heading', { name: /Your Profile/i })).toHaveCount(0);
  });
});
```

**Key patterns:**
- Cookie acceptance helper called before interactions
- `waitForTimeout` for async navigation/middleware redirects
- Bi-conditional assertions for optional redirect behavior
- `authenticatedPage` fixture for auth-gated tests
- `page.evaluate()` for reading localStorage state

### API Integration Test Patterns

File: `frontend/tests/e2e/api-integration.spec.ts`

```typescript
test.describe('API Integration Tests (Mocked)', () => {
  test('should fetch all fragrances with mocked API', async ({ apiMockedPage }) => {
    const page = apiMockedPage;
    await page.goto('/fragrances');
    await page.waitForTimeout(1000);
    expect(page.url()).toContain('/fragrances');
  });

  test('should handle 404 errors gracefully when fragrance not found', async ({ apiMockedPage }) => {
    const page = apiMockedPage;
    await page.goto('/fragrances/nonexistent-id');
    const body = await page.textContent('body');
    expect(body).toBeTruthy();
  });

  test('should timeout gracefully if API takes too long', async ({ apiMockedPage }) => {
    const page = apiMockedPage;
    await page.route('**/api/fragrances', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      route.continue();
    });
    await page.goto('/fragrances');
    expect(page.url()).toContain('/fragrances');
  });
});
```

### E2E Coverage Summary

| Area | Tests | Approach |
|------|-------|----------|
| Home page | 1 test, 3 visual | Visible headings, CTAs |
| Public discovery | 1 test | Navigate to /fragrances, /families |
| Auth/Register | 1 test + 1 visual | Form validation |
| Auth/Login | 1 test + 1 visual | Invalid email validation |
| Profile guard | 1 test | Auth redirect check |
| Recommendations guard | 1 test | Auth guard UX |
| Auth flow | 2 tests + 1 visual | Login/logout cycle |
| Mobile viewport | 1 test | 375px width rendering |
| API mocking | 8 tests | Mocked endpoints, 404, timeout, concurrent, validation |
| Visual regression | 30 snapshots | 11 pages × 3 breakpoints |

### Testing Gaps (based on exploration)

- **No unit tests for frontend** — No Jest/Vitest config. Only E2E tests exist.
- **Frontend store** (`app-store.ts`) has no isolated tests for the komplex adaptive quiz state logic.
- **Backend tests** do not cover the large `fragrances.py` router's filtering logic (`_catalog_filtered_rows_from_list`) extensively.
- **No test for the dead endpoints** — `recommend_by_text()`, `recommend_by_profile()` (known to raise 503).
- **`npm test` does not work** — AGENTS.md states it fails; `npm run test:e2e` is the correct command.
- **ML tests** (`ml/tests/`) exist (test_graph, test_integration) but weren't analyzed in depth here.

---

## ML Testing

Not analyzed in depth. The `ml/tests/` directory contains:
- `test_graph.py` — graph validation (run via `python -m ml.tests.test_graph --profile local`)
- `test_integration.py` — end-to-end pipeline test (run via `python -m ml.tests.test_integration --cleanup --profile local`)

---

*Testing analysis: 2026-05-21*
