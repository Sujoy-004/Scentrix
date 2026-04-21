# Testing Strategy

## Backend
- **Framework**: `pytest` + `pytest-asyncio`
- **Coverage**: Targets 80%+ on API routers and services.
- **Verification**: 
  - Unit tests for services and Integration tests for Celery.
  - CI Gates: `ruff format --check`, `ruff check`, and `mypy`.
  - **Implicit Requirement**: `pip install -e ".[dev,runtime]"` must be run in CI.
- **Running**: `make test-backend`


## Frontend
- **Framework**: Playwright (E2E)
- **Unit**: (Note: root Makefile references Jest but codebase uses Playwright for core flows).
- **Running**: `npm run test:e2e`

## ML
- **Audit**: `ml/pipeline/diversity_audit.py` for dataset quality verification.
