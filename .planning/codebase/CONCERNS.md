# Development Concerns

## Critical Vulnerabilities
- **PII Leakage**: Risk of storing unencrypted user emails if `DataVault` is bypassed.
- **Neural Timeouts**: 300ms SLA for discovery engine requires strict circuit breakers on Pinecone/Neo4j calls.

## Current Tech Debt
- **Scraper Sniping**: Dependency on Fragrantica HTML structure is brittle.
- **Context Fragmentation**: Older `_brain` folders scattered in sub-directories (Cleared by Antigravity at 2026-04-21).
- **Missing E2E CI**: Frontend E2E tests are not yet fully integrated into standard `make lint` cycles.
