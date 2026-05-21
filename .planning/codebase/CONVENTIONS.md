# Coding Conventions

**Analysis Date:** 2026-05-21

## Language Overview

The codebase spans three languages with distinct ecosystems:

| Language | Location | Framework | Linter/Formatter |
|----------|----------|-----------|-----------------|
| Python 3.11+ | `backend/`, `ml/` | FastAPI, PyTorch | ruff + mypy |
| TypeScript 5.9 | `frontend/` | Next.js 16, React 19 | ESLint + Prettier |
| TypeScript | `frontend/tests/` | Playwright | Part of ESLint config |

---

## Backend Python Conventions

### Naming Patterns

**Files:**
- Use `snake_case.py` — e.g., `fragrances.py`, `hybrid_search.py`, `job_store.py`
- Exception: `__init__.py`, `conftest.py` (pytest conventions)

**Functions and Methods:**
- Use `snake_case` — e.g., `verify_password`, `get_current_user_id`, `_catalog_filtered_rows`
- Private helpers prefixed with `_` underscore — e.g., `_matches_text`, `_safe_pct`, `_parse_context_json`
- Async functions use `async def` — e.g., `async def get_catalog()`

**Variables:**
- Use `snake_case` — e.g., `query_norm`, `brand_norm`, `match_score`
- Module-level constants: `UPPER_CASE` — e.g., `TEST_DATABASE_URL`, `DB_AVAILABLE`, `ML_ENABLED`
- Module-level caches: prefixed with `_` underscore — e.g., `_catalog_embeddings_cache`, `_is_hydrating`

**Classes:**
- Use `PascalCase` — e.g., `Settings`, `HybridRecommender`, `TokenPayload`, `User`, `TextEncoder`
- Pydantic models: `PascalCase` — e.g., `UserRegister`, `FragranceCatalogItem`, `StandardResponse`

**Types:**
- Type hints required (mypy `check_untyped_defs = true`)
- Use `list[X]` not `List[X]` (Python 3.11 style) — e.g., `list[dict[str, Any]]`
- Use `X | None` not `Optional[X]` — e.g., `str | None = None`
- Use `collections.abc` for ABCs — e.g., `from collections.abc import AsyncIterator, AsyncGenerator`

### Code Style

**Formatter:** ruff with line-length 100 (configured in `backend/ruff.toml` and `backend/pyproject.toml`)

**Linter:** ruff with these rule sets:
- `E` — pycodestyle errors
- `W` — pycodestyle warnings
- `F` — pyflakes
- `I` — isort
- `C` — flake8-comprehensions
- `B` — flake8-bugbear
- `UP` — pyupgrade

**Ignored rules:**
- `E501` — line too long (handled by formatter)
- `B008` — function calls in argument defaults (blocked by FastAPI `Depends()` pattern)

**Complexity:** max-complexity = 20 (configured in `backend/ruff.toml`)

**Type checker:** mypy with strict settings:
- `check_untyped_defs = true`
- `disallow_incomplete_defs = true`
- `warn_return_any = true`
- `no_implicit_optional = true`
- `warn_unused_ignores = true`
- Ignored imports: `neo4j.*`, `pinecone.*`, `ml.*` (no stubs available)

**Per-file ignores:** `__init__.py` allows `F401` (unused imports for re-exports)

### Import Organization

Pattern observed across all backend files:
1. Standard library imports (e.g., `logging`, `json`, `os`, `sys`)
2. Third-party imports (e.g., `fastapi`, `sqlalchemy`, `pydantic`, `httpx`)
3. Application imports (e.g., `from app.config import settings`)

Groups separated by blank lines. No `isort`-enforced ordering beyond group separation.

Example from `backend/app/routers/fragrances.py`:
```python
import json
import logging
import os
import sys
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_id, get_optional_user_id
from app.config import settings
from app.database import get_session
from app.models.models import UserInteractionEvent
```

### Module Design

**Exports:**
- Re-exports via `__init__.py` files in `app/`, `app/routers/`, `app/schemas/`, `app/auth/`, `app/models/`, `app/services/`
- `app/schemas/__init__.py` and `app/routers/__init__.py` exist in the package structure
- Module docstrings at top of every file documenting purpose — e.g., `"""Authentication utilities and JWT handling."""`

**Barrel Files:** Minimal; `app/models/__init__.py`, `app/routers/__init__.py`, `app/services/__init__.py` are mostly empty or re-export

### Error Handling

**Strategy:** Graceful degradation with fallback chains

**Patterns:**
- Routers implement fallback chains: Graph DB → JSON catalog → error
- `try/except` blocks with specific exception types, not bare `except:`
- Failed external services logged but don't crash the request
- Common pattern in `backend/app/routers/fragrances.py`:
```python
try:
    results = client.execute_query(query, params)
    if results:
        # use results
        return {"status": "success", "data": data}
except Exception as e:
    logger.error(f"Keyword search failed: {e}")
# Fallback
fallback_rows = _catalog_filtered_rows(...)
```

**HTTP Exceptions:**
- Standard FastAPI `HTTPException` with status codes (`404`, `401`, `403`, `409`, `500`)
- Custom `HTTPException` handler in `backend/app/main.py` that returns `{"status": "error", "code": ..., "message": ...}`
- Universal exception handler returns `500` for unhandled errors

**DB Availability:**
- Graceful offline mode: `DB_AVAILABLE` flag in `backend/app/database.py`
- Session dependency yields `None` when DB is down
- Routes check DB availability and use fallbacks

### Logging

**Framework:** Standard `logging` module
- `logging.basicConfig(...)` configured in `backend/app/main.py`
- Format: `"%(asctime)s [%(name)s] %(levelname)s: %(message)s"`
- Per-module loggers: `logger = logging.getLogger(__name__)`
- Sentry integration via `backend/app/sentry_config.py`

**Patterns:**
- `logger.info` for startup and lifecycle events
- `logger.warning` for degraded modes
- `logger.error` with `exc_info=True` for exceptions
- `logger.debug` for semantic search bypass events

### Configuration

**Framework:** `pydantic-settings` (class `Settings` in `backend/app/config.py`)
- Loads from `.env` file with `env_file=".env"`
- `case_sensitive=False`, `extra="ignore"`
- Supports alias choices for env vars (e.g., `NEO4J_URI | NEO4J_URL`)
- `field_validator` for URL normalization
- Singleton: `settings = Settings()` at module level

### SQLAlchemy Models

**Base class:** `Base(DeclarativeBase)` in `backend/app/models/models.py`
- `from __future__ import annotations` for deferred annotations
- `Mapped[X]` typed column declarations
- `utc_now()` helper using `datetime.now(UTC).replace(tzinfo=None)`
- `__repr__` on every model
- `onupdate=utc_now` for `updated_at` columns
- GDPR-aware: `encrypted_full_name`, `encrypted_email`, `email_hash`

### Pydantic Schemas

**Style:** `backend/app/schemas/schemas.py`
- Section dividers: `# ======...` comment blocks for schema groups
- `model_config = ConfigDict(from_attributes=True)` for ORM mapping
- `model_config = ConfigDict(extra="ignore")` for update payloads
- `Field(..., min_length=..., max_length=...)` for validation
- `EmailStr` from pydantic for email fields

### Alembic Migrations

- Located in `backend/app/migrations/versions/`
- Named sequentially: `001_initial_setup.py`, `002_add_user_interaction_events.py`, etc.
- Each migration has a descriptive revision message

### ML Code Conventions

**Files in `ml/`:**
- SAFE MODE pattern for optional dependencies — graceful fallback when torch/pinecone not installed:
```python
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    class SentenceTransformer:
        def __init__(self, *args, **kwargs): pass
        def encode(self, *args, **kwargs): return []
```
- Module-level caches: `_catalog_embeddings_cache = None`
- Conditional numpy: `try: import numpy as np; except: np = None`
- `# SAFE MODE: Conditional import` comments mark optional dependency blocks

---

## Frontend TypeScript/React Conventions

### Naming Patterns

**Files:**
- Components: `PascalCase.tsx` — e.g., `FragranceCard.tsx`, `HeroSection.tsx`, `Navbar.tsx`
- Pages: `page.tsx` inside route directories — e.g., `src/app/quiz/page.tsx`
- Hooks: `camelCase.ts` — e.g., `hooks.ts`, `api.ts`, `quizTheme.ts`
- Types: `camelCase.ts` — e.g., `collection.ts`, `dom.d.ts`
- Config: `playwright.config.ts`, `eslint.config.mjs`

**Functions and Variables:**
- `camelCase` for functions, variables, and React hooks — e.g., `handleSaveToggle`, `isSaved`, `useAppStore`
- React components: `PascalCase` — e.g., `function FragranceCard({ frag, index })`
- Custom hooks prefixed with `use` — e.g., `useLogin`, `useWishlist`, `useAddToCollection`
- Event handlers prefixed with `handle` — e.g., `handleSaveToggle`

**Types and Interfaces:**
- `PascalCase` — e.g., `FragranceCardProps`, `QuizResponse`, `UserPreferences`, `AdaptiveQuizState`
- Interface names are nouns or noun phrases
- Type aliases used sparingly (prefer `interface`)

**Constants:**
- `UPPER_CASE` — e.g., `BASE_URL`, `VALID_IDS`, `BREAKPOINTS`, `DEFAULT_ADAPTIVE_QUIZ`

### Code Style

**Formatter:** Prettier (configured in `frontend/.prettierrc`):
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

**Linter:** ESLint v9 with `eslint-config-next` (core-web-vitals + TypeScript):
- `@typescript-eslint/no-explicit-any`: `warn` (temporary baseline)
- `react/no-unescaped-entities`: `warn`
- `react-hooks/set-state-in-effect`: `warn`

**TypeScript:**
- `strict: true` in `tsconfig.json`
- Path alias `@/*` maps to `./src/*`
- `target: ES2017`, `moduleResolution: bundler`
- `jsx: react-jsx` (React 19 JSX transform)

### Import Organization

**Order:**
1. React/Next.js imports (e.g., `'use client'`, `import { motion } from 'framer-motion'`)
2. Third-party library imports (e.g., `axios`, `zustand`, `@tanstack/react-query`)
3. Application imports using `@/` alias — e.g., `import { useAppStore } from '@/stores/app-store'`

**Path Aliases:**
- `@/` → `./src/*` — used for all internal imports
- No relative imports like `../../` observed in components

### State Management

**Framework:** Zustand with `persist` middleware (`frontend/src/stores/app-store.ts`)
- Named export: `export const useAppStore`
- Actions defined inline in the store creator function
- `partialize` to whitelist persisted fields
- SSR-safe localStorage with no-op fallback for `window === undefined`
- Sections organized with comments: `// ── State defaults ─────`, `// ── Quiz actions ─────`

**Server State:** TanStack React Query (`@tanstack/react-query`)
- Custom hooks prefixed with `use` — e.g., `useWishlist`, `useRecommendations`, `useFragranceCatalog`
- `queryKey` arrays with relevant dependencies
- `mutationFn` for write operations
- `staleTime: 5 min`, `gcTime: 10 min` (configured in `Providers.tsx`)

### Component Design

**React 19 features:**
- `'use client'` directive for client components
- Functional components with hooks
- Default exports for pages; named exports for components

**Patterns:**
- Destructured props with TypeScript interfaces
- `useRef` for DOM references (`cardRef`)
- `motion` from framer-motion for animations
- Inline styles for dynamic values; Tailwind v4 classes for static styling
- `useRouter` from `next/navigation` for navigation

**Component Structure:**
```tsx
'use client';
import React, { useRef, useEffect } from 'react';
// ... more imports

interface ComponentProps {
  prop1: type;
}

export function ComponentName({ prop1 }: ComponentProps) {
  // Hooks
  // Event handlers
  // Render
}
```

### API Layer

**File:** `frontend/src/lib/api.ts`
- Axios instance with `baseURL` from `NEXT_PUBLIC_API_URL`
- 60s timeout (for "deep neural synthesis")
- Request interceptor for JWT token injection
- All methods wrapped in try/catch with fallback returns
- Non-blocking patterns: guest flow must never crash
- Export object `api` with named methods

### Error Handling in Frontend

**Pattern:** Non-blocking optimistic behavior
- API failures return default values (`null`, `[]`, `{ items: [], total: 0 }`)
- `console.warn` for recoverable failures, `console.error` for unrecoverable
- Guest flow must never crash — rating sync failures are swallowed
- React Query `retry` logic with conditional retry (skip 403s):
```tsx
retry: (failureCount, error: any) => {
  if (error?.response?.status === 403) return false;
  return failureCount < 2;
}
```

### Perceptual Naming Convention

The codebase uses distinctive identifiers for components and files:
- `StringTuneManager` — text/font tuning component
- `PostHogPageView` — analytics page view tracker
- `DiscoveryNeuralLoader` — loading state component
- `VideoScrubber` — video background component
- `CookieBanner` — GDPR consent banner
- `PageTransition` — route transition animation wrapper
- `ScentrixLogo` — branded SVG logo

### CSS/Styling

- Tailwind CSS v4 for all styling (`frontend/src/app/globals.css`)
- `@tailwindcss/postcss` PostCSS plugin
- Motion animations via framer-motion library
- Scoped CSS via Tailwind utility classes
- Conditional class strings with template literals

---

## Cross-Cutting Conventions

### API Standard Response Envelope

All backend API responses follow:
```json
{
  "status": "success" | "error",
  "data": { ... },
  "code": 200,
  "message": "..."
}
```
Defined in `backend/app/schemas/schemas.py` via `StandardResponse` Pydantic model.

### Module Docstrings

Every Python module and every function with non-trivial logic has a docstring:
- Module: `"""Short module description."""`
- Function: `"""Short description.\n\nArgs:\n    arg: Description\n\nReturns:\n    Description\n\nRaises:\n    ExceptionType: When/why\n"""`

### JSDoc/TSDoc

Used sparingly in frontend; no consistent pattern beyond occasional inline comments.
Playwright test files have extensive block comments explaining test groups and snapshot maintenance.

### Comments

- `# TODO/FIXME/HACK/XXX` markers exist but are rare in source code
- Business logic comments explain "why" not "what"
- Markers like `# Server-side vs client-side` comments for SSR boundaries
- `// Performance optimization` comments for deliberate omissions
- Large comment blocks for disabled features (PostHog, Sentry warmup)

### Git Conventions

- `.gitignore` at root excludes `node_modules/`, `.next/`, `__pycache__/`, `.pytest_cache/`
- `.dockerignore` for Docker build context
- `Makefile` for common development commands
- `.github/prompts/` contains brand/persona prompts for AI coding sessions

---

*Convention analysis: 2026-05-21*
