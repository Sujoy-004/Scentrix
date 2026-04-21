# Testing Strategy

## Backend
- **Framework**: `pytest` + `pytest-asyncio`
- **Coverage**: Targets 80%+ on API routers and services.
- **Types**: 
  - Unit tests for services.
  - Integration tests for Celery tasks and database workflows.
- **Running**: `make test-backend`

## Frontend
- **Framework**: Playwright (E2E)
- **Unit**: (Note: root Makefile references Jest but codebase uses Playwright for core flows).
- **Running**: `npm run test:e2e`

## ML
- **Audit**: `ml/pipeline/diversity_audit.py` for dataset quality verification.
