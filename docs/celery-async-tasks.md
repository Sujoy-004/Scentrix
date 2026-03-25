"""Celery & Async Task Processing - Backend T2.6

## Overview

ScentScape uses Celery for async recommendation generation and ML inference.
Tasks run on background workers while the API responds immediately with a job ID.
Results are cached in Redis for fast polling.

## Tasks

### 1. recommend_by_text_task
**Purpose:** Generate recommendations from natural language query

**Input:**
- job_id: Unique identifier
- query: "Fresh, citrusy, not too sweet"
- limit: 10 (default)
- user_id: Optional (for personalization)

**Process:**
1. Encode query with Sentence-BERT (all-MiniLM-L6-v2)
2. Search Pinecone for similar fragrance description embeddings
3. Fetch fragrance details from Neo4j
4. Apply user taste vector if authenticated (BPR ranking)
5. Return top-K results

**Time:** ~2-5 seconds
**Output:** Ranked list of fragrances with similarity scores

### 2. recommend_by_profile_task
**Purpose:** Generate personalized recommendations from user's ratings

**Input:**
- job_id: Unique identifier
- user_id: Authenticated user
- limit: 10 (default)

**Process:**
1. Fetch user's fragrance ratings from PostgreSQL
2. Build user taste vector from rating dimensions
3. Get all fragrance embeddings from GraphSAGE
4. Score fragrances via cosine similarity
5. Apply BPR ranking for personalization
6. Filter out already-rated fragrances
7. Return top-K new recommendations

**Time:** ~5-10 seconds
**Output:** Ranked personalized fragrance list

### 3. generate_user_embeddings_task
**Purpose:** Pre-compute and cache user embeddings for fast recommendations

**Input:**
- user_id: User to generate embeddings for

**Process:**
1. Fetch user's fragrance ratings
2. Build taste vector from rating dimensions
3. Cache in Redis (24h TTL)

**Time:** ~1-2 seconds
**Output:** Cached embedding vector in Redis

## Setup

### 1. Install Celery
```bash
pip install celery==5.3.4 redis==5.0.0
```

### 2. Start Redis
```bash
# Using Docker (from project root)
docker-compose up redis -d

# Or locally
redis-server
```

### 3. Start Celery Worker
```bash
# In project root
celery -A app.celery_app worker -l info

# With queue specification
celery -A app.celery_app worker -Q recommendations,ml -l info

# Multiple workers (for parallelism)
celery -A app.celery_app worker -c 4 -l info  # 4 concurrent tasks
```

### 4. Optional: Start Celery Beat (for periodic tasks)
```bash
celery -A app.celery_app beat -l info
```

### 5. Optional: Flower (task monitoring)
```bash
pip install flower
celery -A app.celery_app flower

# Visit http://localhost:5555
```

## Environment Variables

```bash
# Celery broker (Redis)
CELERY_BROKER_URL=redis://localhost:6379/0

# Celery results backend (Redis)
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Optional: Sentry for error tracking
SENTRY_DSN=https://...
```

## Monitoring Tasks

### View Active Tasks
```bash
celery -A app.celery_app inspect active
```

### View Registered Tasks
```bash
celery -A app.celery_app inspect registered
```

### View Task Stats
```bash
celery -A app.celery_app inspect stats
```

### Purge Queue (admin only)
```bash
celery -A app.celery_app purge
```

## Task Flow (In Recommendations Router)

```
POST /fragrances/recommend/text
    │
    ├─ Create job_id
    ├─ Send to Celery: recommend_by_text_task(job_id, query, user_id)
    └─ Return: {"job_id": "...", "status": "processing"}

GET /recommendations/{job_id}
    │
    ├─ Check Redis cache for results
    ├─ If processing: Return {"status": "processing", ...}
    ├─ If completed: Return {"fragrances": [...], ...}
    └─ If failed: Return error
```

## Error Handling

Tasks are configured with:
- **max_retries:** 3 (attempts)
- **retry_delay:** 60 seconds (between attempts)
- **timeout:** None (will not timeout, but can be configured)

On failure:
1. Task retried up to max_retries
2. Error logged with full traceback
3. Job status set to "failed" in Redis
4. Error message returned to client

## Performance Notes

### Concurrency
- Default: 1 task at a time (worker_prefetch_multiplier=1)
- Recommendation tasks are I/O bound (network, DB queries)
- Can increase worker concurrency if needed:
  ```bash
  celery -A app.celery_app worker -c 8
  ```

### Memory
- Each task loads models into memory (Sentence-BERT, GraphSAGE)
- Models should be loaded once and shared across tasks
- Consider using task pools for large-scale deployments

### Caching
- Results cached in Redis for 24 hours
- User embeddings cached in Redis (24h TTL)
- Pinecone index cached locally for fast ANN search

## Integration with Flow Routers

The routers (fragrances.py, users.py) integrate Celery like this:

```python
from app.tasks.recommend_tasks import recommend_by_text_task

@router.post("/recommend/text")
async def recommend_by_text(request: TextRecommendationRequest):
    job_id = str(uuid4())
    
    # Send task to Celery
    task = recommend_by_text_task.delay(
        job_id=job_id,
        query=request.query,
        limit=request.limit,
        user_id=user_id,
    )
    
    # Return immediately
    return RecommendationJob(job_id=job_id, status="processing")
```

The task updates Redis with results asynchronously.

## Files

- `app/celery_app.py` — Celery configuration and initialization
- `app/tasks/recommend_tasks.py` — Task implementations
- `app/tasks/__init__.py` — Tasks module exports

## Next Steps (Phase 3)

Phase 3 ML pipeline will:
- Implement actual Sentence-BERT encoding
- Implement GraphSAGE embedding generation
- Integrate Pinecone similarity search
- Implement BPR ranking logic
- Cache user embeddings automatically
"""
