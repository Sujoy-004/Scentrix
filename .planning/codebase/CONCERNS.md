# Development Concerns

## Critical Vulnerabilities
- **PII Leakage**: Risk of storing unencrypted user emails if `DataVault` is bypassed.
- **Neural Timeouts**: 300ms SLA for discovery engine requires strict circuit breakers on Pinecone/Neo4j calls.

## Current Tech Debt
- **Scraper Sniping**: Dependency on Fragrantica HTML structure is brittle.
- **Context Fragmentation**: Older `_brain` folders scattered in sub-directories (Cleared by Antigravity at 2026-04-21).
## CI/CD Fragility
- **Dependency Drift**: Build-time failures occurred due to `numpy` being an optional [runtime] dependency not installed during CI `mypy` checks.
- **Workflow YAML Formatting**: Incorrect indentation in CI workflow files can block the entire pipeline.
- **Node.js Deprecations**: GitHub Actions runners are moving towards Node 24; several existing actions (Checkout v4, Setup-Python v4) will require monitoring.

## Specific Implementation Gotchas
- **Mypy Shadowing**: Reusing variables in different scopes (e.g., `user` in Supabase vs. local path) can cause "Incompatible types in assignment" if the first assignment's type is narrower than subsequent ones.
- **Ruff Formatting**: Code pushed without local `ruff format` will fail the Backend Quality Gate.
