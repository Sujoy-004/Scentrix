---
type: community
members: 55
---

# Community 4

**Members:** 55 nodes

## Members
- [[.__init__()]] - code - Scentrix\backend\app\cache.py
- [[.__init__()_2]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[.__init__()_10]] - code - Scentrix\ml\models\text_encoder.py
- [[._ensure_index()_2]] - code - Scentrix\ml\models\text_encoder.py
- [[._get_encoder()]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[._get_item_text()]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[._query_vector_dna()]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[._rerank_genetic_match()]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[.close()]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[.delete()]] - code - Scentrix\backend\app\cache.py
- [[.generate_embeddings()]] - code - Scentrix\ml\models\text_encoder.py
- [[.get_recommendations()]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[.get_redis()]] - code - Scentrix\backend\app\cache.py
- [[.process_and_upload()]] - code - Scentrix\ml\models\text_encoder.py
- [[.warmup()]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[Encode texts into vectors.]] - rationale - Scentrix\ml\models\text_encoder.py
- [[Ensure the Pinecone index exists, create if it doesn't._1]] - rationale - Scentrix\ml\models\text_encoder.py
- [[Generate embeddings for fragrance descriptions and upload to Pinecone.]] - rationale - Scentrix\ml\models\text_encoder.py
- [[Generate recommendations from user quiz ratings.      Strategy (in priority or]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[HybridRecommender]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[Initialize SentenceTransformer and Pinecone client.]] - rationale - Scentrix\ml\models\text_encoder.py
- [[Main entry point for 300ms Adaptive Discovery.]] - rationale - Scentrix\backend\app\services\hybrid_search.py
- [[Neural Engine Access the ML Encoder via the global recommender service.]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[Persist a quiz rating for authenticated users.     For guests this is a silent]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[Persist multiple quiz ratings at once. Used during Guest - User conversion.]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[Phase 1 High-recall dual-vector search (Text DNA + Graph DNA).]] - rationale - Scentrix\backend\app\services\hybrid_search.py
- [[Phase 2 High-precision graph reranking using genetic distance.]] - rationale - Scentrix\backend\app\services\hybrid_search.py
- [[Pre-cache catalog embeddings at startup.]] - rationale - Scentrix\backend\app\services\hybrid_search.py
- [[Proxy for the recommender service text extractor.]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[Proxy for the recommender service warmup.]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[Rebuild text and graph embeddings from the current seed dataset.]] - rationale - Scentrix\backend\app\tasks\recommend_tasks.py
- [[RedisCache]] - code - Scentrix\backend\app\cache.py
- [[Remove fragrance from user's collection.      Args         saved_id Saved f]] - rationale - Scentrix\backend\app\routers\users.py
- [[Return neural recommendations for guest users using the Hybrid Engine.]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[Return personalized recommendations for an authenticated user.]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[Strip common prefix variants so IDs match the catalog.]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[TextEncoder]] - code - Scentrix\ml\models\text_encoder.py
- [[Unified 'Aetheric' DNA Recommender (Text + Graph Fusion).      Targets 300ms SLA]] - rationale - Scentrix\backend\app\services\hybrid_search.py
- [[_get_item_text()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[_normalize_id()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[_score_catalog()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[cache.py]] - code - Scentrix\backend\app\cache.py
- [[get_encoder()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[get_guest_recommendations()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[get_personalized_recommendations()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[hybrid_search.py]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[load_recommendation_catalog()]] - code - Scentrix\backend\app\services\catalog.py
- [[main()_3]] - code - Scentrix\ml\sync_pinecone.py
- [[rebuild_embeddings_task()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[remove_saved_fragrance()]] - code - Scentrix\backend\app\routers\users.py
- [[submit_batch_ratings()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[submit_fragrance_rating()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[sync_pinecone.py]] - code - Scentrix\ml\sync_pinecone.py
- [[text_encoder.py]] - code - Scentrix\ml\models\text_encoder.py
- [[warmup_neural_engine()]] - code - Scentrix\backend\app\routers\recommendations.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_4
SORT file.name ASC
```

## Connections to other communities
- 19 edges to [[_COMMUNITY_Community 0]]
- 12 edges to [[_COMMUNITY_Community 1]]
- 4 edges to [[_COMMUNITY_Community 5]]
- 4 edges to [[_COMMUNITY_Community 3]]
- 2 edges to [[_COMMUNITY_Community 7]]
- 1 edge to [[_COMMUNITY_Community 6]]
- 1 edge to [[_COMMUNITY_Community 17]]
- 1 edge to [[_COMMUNITY_Community 13]]

## Top bridge nodes
- [[load_recommendation_catalog()]] - degree 17, connects to 4 communities
- [[rebuild_embeddings_task()]] - degree 7, connects to 3 communities
- [[get_personalized_recommendations()]] - degree 13, connects to 2 communities
- [[get_guest_recommendations()]] - degree 11, connects to 2 communities
- [[_score_catalog()]] - degree 11, connects to 2 communities