# Codebase Structure

```text
.
├── .github/              # CI/CD and AI Persona configs
├── .planning/            # AI dynamic context (this folder)
├── artifacts/            # Generated reports/scratchpad
├── backend/
│   ├── app/              # FastAPI core logic (routers, models, services)
│   ├── tests/            # Pytest suite
│   └── alembic.ini       # Migration config
├── docs/                 # Historical records and audit logs
├── frontend/             # Next.js 15 app
│   ├── src/app/          # App router pages
│   └── src/components/   # Shared UI components
├── graphify-out/         # Universal Context (Codebase Map)
├── internal/             # Internal monitoring and personality tools
├── ml/                   # Primary ML logic and Neo4j ingestion
└── scripts/              # Utility scripts for data normalization

```
