---
type: community
members: 16
---

# Community 14

**Members:** 16 nodes

## Members
- [[Async recommendation job response.]] - rationale - Scentrix\backend\app\schemas\schemas.py
- [[Generate recommendation from text description (async job).      Uses Sentence-]] - rationale - Scentrix\backend\app\routers\fragrances.py
- [[Generate recommendations based on user's fragrance ratings (async job).      R]] - rationale - Scentrix\backend\app\routers\fragrances.py
- [[Poll async recommendation job result.      Args         job_id Job ID from]] - rationale - Scentrix\backend\app\routers\fragrances.py
- [[RecommendationJob]] - code - Scentrix\backend\app\schemas\schemas.py
- [[Redis-backed job store for recommendation lifecycle tracking.]] - rationale - Scentrix\backend\app\services\job_store.py
- [[_get_client()]] - code - Scentrix\backend\app\services\job_store.py
- [[_job_key()]] - code - Scentrix\backend\app\services\job_store.py
- [[create_job()]] - code - Scentrix\backend\app\services\job_store.py
- [[get_job()]] - code - Scentrix\backend\app\services\job_store.py
- [[get_recommendation_result()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[is_job_timed_out()]] - code - Scentrix\backend\app\services\job_store.py
- [[job_store.py]] - code - Scentrix\backend\app\services\job_store.py
- [[recommend_by_profile()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[recommend_by_text()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[update_job()]] - code - Scentrix\backend\app\services\job_store.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_14
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Community 1]]
- 3 edges to [[_COMMUNITY_Community 5]]
- 2 edges to [[_COMMUNITY_Community 0]]
- 1 edge to [[_COMMUNITY_Community 3]]

## Top bridge nodes
- [[get_recommendation_result()]] - degree 8, connects to 3 communities
- [[RecommendationJob]] - degree 6, connects to 1 community
- [[recommend_by_profile()]] - degree 5, connects to 1 community
- [[recommend_by_text()]] - degree 5, connects to 1 community
- [[_get_client()]] - degree 5, connects to 1 community