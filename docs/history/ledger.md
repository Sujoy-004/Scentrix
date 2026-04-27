# Scentrix Deployment Ledger

## System Architecture Table
| Module | Technology | Provider | Status |
| :--- | :--- | :--- | :--- |
| **Frontend** | Next.js (TS) | Vercel | [scentrix-one.vercel.app](https://scentrix-one.vercel.app) |
| **Backend API** | FastAPI (Py) | Railway | [Scentrix Backend](https://scentrix-production.up.railway.app) |
| **Database** | PostgreSQL | Supabase | Connected (Session Pooler) |
| **Graph DB** | Neo4j | Aura DB | Verified Fallback Active (21k fragrances) |
| **Vector Search** | Pinecone | Serverless | Neural Ranking Active |
| **Task Queue** | Celery + Redis | Railway | [NameError Fix Verified] |

## Phase E & F: Stabilization (SUCCESS)
- **Status**: Completed
- **Actions**:
    - Migrated to Supabase Session Pooler (Port 5432) to support `asyncpg` with Transaction Isolation.
    - Resolved `DuplicatePreparedStatementError` by disabling the statement cache.
    - Fixed critical startup NameErrors in `celery_app.py` (`Celery` and `os` imports).
    - Optimized environment variables for production environment aliasing.

## Phase G: Final Flight Proof (VERIFIED)
- **Status**: Mission Accomplished
- **Verification Proof**:
    - **Backend Logs**: `Uvicorn running on 0.0.0.0:8080`, `21961 fragrances hydrated`.
    - **Frontend Quiz**: Fully operational. First discovery card (*a-oud-ancienne*) rendered successfully.
- **Flight ID**: `a5b6531`

---
### 🏁 Status: MISSION ACCOMPLISHED 🚀
The Scentrix platform is fully operational in production. The neural discovery engine is live, and the atmosphere is ready for exploration.
