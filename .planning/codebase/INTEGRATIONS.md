# External Integrations

## Core Infrastructure
- **PostgreSQL**: Primary SQL store for users and ratings.
- **Neo4j**: Knowledge Graph for fragrance relationships (notes, accords, brands).
- **Redis**: Caching for Recommendation jobs and Quiz session state.

## Third-Party Services
- **Supabase Auth**: External identity provider. Backend verifies JWTs and syncs profiles.
- **Pinecone**: Vector database for Text DNA similarity search.
- **Sentry**: Error reporting (configured in `backend/app/services/sentry_config.py`).
- **Cloudflare R2**: (Optional/Legacy references found in scraper snippets).
