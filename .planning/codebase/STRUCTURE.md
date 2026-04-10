# Project Structure

## Layout
```
/frontend
  ├── src/app/          - Next.js 15+ App Router definitions
  ├── src/components/   - Shared React components
  ├── public/           - Static assets
  └── eslint, tailwind  - Tooling configs

/backend
  ├── app/              - FastAPI application package
  │    ├── services/    - Business logic
  │    └── schemas/     - Pydantic models
  ├── scripts/          - Standalone util scripts
  └── pyproject.toml    - Hatchling config

/ml
  ├── data/             - Raw/processed data sets
  ├── flows/            - Prefect data flows
  ├── graph/            - Neo4j graph generation
  ├── models/           - ML core inferencing
  ├── pipeline/         - ETL
  └── scraper/          - Scrapy definitions
```

## Key Locations
- Entrypoint frontend: `frontend/src/app/`
- Entrypoint backend: `backend/app/main.py`
- ML synthetic runner: `ml/generate_synthetic_data.py`
