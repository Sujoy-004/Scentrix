# External Integrations

## Databases
- **PostgreSQL**: Relational datastore (via asyncpg/SQLAlchemy).
- **Redis**: Caching and Celery broker for async task queues.
- **Neo4j**: Graph database for hierarchical olfactive mappings.
- **Pinecone**: Vector database for NLP semantic search endpoints.

## Auth & Security
- **JWT**: Custom JWT generation via python-jose, passwords hashed via bcrypt.

## Infrastructure Cloud
- **Vercel**: Frontend deployment implicitly supported via Next.js and configuration (`vercel.json`).
- **AWS**: S3 and object storage via `boto3`.
- **Railway**: Implicit backend target (`railway.toml`).

## External APIs
- **Scent/Fragrance Sources**: Scraped dynamically via custom Scrapy pipelines.
