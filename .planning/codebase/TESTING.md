# Testing Strategy

## Frontend Testing
- **E2E/Integration**: Playwright is primary framework (`test:e2e`, `test:e2e:ui`).
- **Mocking**: MSW (Mock Service Worker) integrated for intercepting and mocking API requests during component isolation rendering.
- Code coverage handled independently or bypassed in favor of core logic E2E.

## Backend Testing
- **Framework**: `pytest`, configured for `asyncio_mode = auto` (FastAPI endpoints).
- **Execution**: Target is `tests/` directory with coverage tracking via `pytest-cov`.
- Test commands ensure execution runs coverage metrics to ensure service business layer integrity.

## ML Testing
- Has isolated `tests/` directory within the ML stack to independently verify graph mutations and scraping output stability.
