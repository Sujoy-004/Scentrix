---
type: community
members: 41
---

# Community 7

**Members:** 41 nodes

## Members
- [[.on_failure()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[.on_retry()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[.on_success()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[CallbackTask]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[Celery tasks for recommendation generation and ML inference.  T2.6 Async reco]] - rationale - Scentrix\backend\app\tasks\recommend_tasks.py
- [[Deterministically split rows into trainvaltest partitions.]] - rationale - Scentrix\backend\app\tasks\recommend_tasks.py
- [[Generate and cache user taste vector embeddings.      Called periodically for]] - rationale - Scentrix\backend\app\tasks\recommend_tasks.py
- [[Generate text-based fragrance recommendations using lexical+profile ranking.]] - rationale - Scentrix\backend\app\tasks\recommend_tasks.py
- [[Generate user-profile recommendations with split-aware taste modeling.]] - rationale - Scentrix\backend\app\tasks\recommend_tasks.py
- [[Load merged catalog large canonical primary + seed fallback.]] - rationale - Scentrix\backend\app\tasks\recommend_tasks.py
- [[Load user ratings in Celery context while tolerating unavailable DB dependencies]] - rationale - Scentrix\backend\app\tasks\recommend_tasks.py
- [[Task]] - code
- [[Task with callbacks for tracking completion.]] - rationale - Scentrix\backend\app\tasks\recommend_tasks.py
- [[Test Celery task for generating user embeddings (synchronous execution)]] - rationale - Scentrix\backend\tests\test_celery.py
- [[Test Celery task for text recommendations]] - rationale - Scentrix\backend\tests\test_celery.py
- [[_build_user_taste_vector()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_cosine_similarity()_1]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_encode_gender()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_fetch_user_ratings()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_fetch_user_ratings_async()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_fragrance_feature_vector()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_fragrance_tokens()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_load_catalog()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_normalize_concentration()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_normalize_year()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_rank_by_profile()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_rank_by_text()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_serialize_recommendation()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_split_train_val_test()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_tokenize()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[_weighted_average()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[generate_user_embeddings_task()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[recommend_by_profile_task()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[recommend_by_text_task()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[recommend_tasks.py]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[test_celery.py]] - code - Scentrix\backend\tests\test_celery.py
- [[test_generate_user_embeddings_task()]] - code - Scentrix\backend\tests\test_celery.py
- [[test_rank_by_profile_excludes_already_rated_items()]] - code - Scentrix\backend\tests\test_celery.py
- [[test_recommend_by_text_task()]] - code - Scentrix\backend\tests\test_celery.py
- [[test_split_train_val_test_is_deterministic_and_total_preserved()]] - code - Scentrix\backend\tests\test_celery.py
- [[test_split_train_val_test_keeps_all_three_partitions_for_small_non_trivial_input()]] - code - Scentrix\backend\tests\test_celery.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_7
SORT file.name ASC
```

## Connections to other communities
- 8 edges to [[_COMMUNITY_Community 3]]
- 2 edges to [[_COMMUNITY_Community 9]]
- 2 edges to [[_COMMUNITY_Community 4]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 8]]

## Top bridge nodes
- [[_fetch_user_ratings()]] - degree 8, connects to 2 communities
- [[_fragrance_tokens()]] - degree 6, connects to 2 communities
- [[recommend_tasks.py]] - degree 22, connects to 1 community
- [[_fragrance_feature_vector()]] - degree 11, connects to 1 community
- [[recommend_by_profile_task()]] - degree 8, connects to 1 community