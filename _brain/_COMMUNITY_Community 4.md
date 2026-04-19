---
type: community
members: 61
---

# Community 4

**Members:** 61 nodes

## Members
- [[.__init__()_2]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[.__init__()_3]] - code - Scentrix\backend\app\services\sommelier.py
- [[.__init__()_9]] - code - Scentrix\ml\models\text_encoder.py
- [[._ensure_index()_2]] - code - Scentrix\ml\models\text_encoder.py
- [[._query_vector_dna()]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[._rerank_genetic_match()]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[.close()]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[.generate_embeddings()]] - code - Scentrix\ml\models\text_encoder.py
- [[.generate_insight()]] - code - Scentrix\backend\app\services\sommelier.py
- [[.get_recommendations()]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[.process_and_upload()]] - code - Scentrix\ml\models\text_encoder.py
- [[Encode texts into vectors.]] - rationale - Scentrix\ml\models\text_encoder.py
- [[Ensure the Pinecone index exists, create if it doesn't._1]] - rationale - Scentrix\ml\models\text_encoder.py
- [[FragranceRecommendation]] - code - Scentrix\backend\app\routers\recommendations.py
- [[Generate a singular, high-fidelity insight for a recommended cohort.]] - rationale - Scentrix\backend\app\services\sommelier.py
- [[Generate an atmospheric, AI-powered insight for a collection of recommendations.]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[Generate embeddings for fragrance descriptions and upload to Pinecone.]] - rationale - Scentrix\ml\models\text_encoder.py
- [[Generate recommendations from user quiz ratings.      Strategy (in priority orde]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[HybridRecommender]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[Initialize SentenceTransformer and Pinecone client.]] - rationale - Scentrix\ml\models\text_encoder.py
- [[Main entry point for 300ms Adaptive Discovery.]] - rationale - Scentrix\backend\app\services\hybrid_search.py
- [[Persist a quiz rating for authenticated users.     For guests this is a silent 2]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[Persist multiple quiz ratings at once. Used during Guest - User conversion.]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[Phase 1 High-recall dual-vector search (Text DNA + Graph DNA).]] - rationale - Scentrix\backend\app\services\hybrid_search.py
- [[Phase 2 High-precision graph reranking using genetic distance.]] - rationale - Scentrix\backend\app\services\hybrid_search.py
- [[Pre-cache catalog embeddings at startup.]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[Rebuild text and graph embeddings from the current seed dataset.]] - rationale - Scentrix\backend\app\tasks\recommend_tasks.py
- [[Return neural recommendations for guest users using the Hybrid Engine.]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[Return personalized recommendations for an authenticated user.]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[Search fragrances by name, brand, or accord.]] - rationale - Scentrix\backend\app\routers\fragrances.py
- [[SommelierInsightResponse]] - code - Scentrix\backend\app\routers\recommendations.py
- [[SommelierService]] - code - Scentrix\backend\app\services\sommelier.py
- [[Strip common prefix variants so IDs match the catalog.]] - rationale - Scentrix\backend\app\routers\recommendations.py
- [[TextEncoder]] - code - Scentrix\ml\models\text_encoder.py
- [[The 'Neural Sommelier' (Aethera) for Scentrix.      Provides atmospheric, AI-pow]] - rationale - Scentrix\backend\app\services\sommelier.py
- [[Unified 'Aetheric' DNA Recommender (Text + Graph Fusion).      Targets 300ms SLA]] - rationale - Scentrix\backend\app\services\hybrid_search.py
- [[_catalog_filtered_rows()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[_cosine_similarity()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[_get_item_text()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[_mock_public_recommendations()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[_normalize_id()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[_score_catalog()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[get_encoder()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[get_guest_recommendations()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[get_personalized_recommendations()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[get_sommelier_insight()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[hybrid_search.py]] - code - Scentrix\backend\app\services\hybrid_search.py
- [[load_recommendation_catalog()]] - code - Scentrix\backend\app\services\catalog.py
- [[main()_3]] - code - Scentrix\ml\sync_pinecone.py
- [[rebuild_embeddings_task()]] - code - Scentrix\backend\app\tasks\recommend_tasks.py
- [[recommendation_for_me()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[recommendation_similarity()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[recommendation_text_search()]] - code - Scentrix\backend\app\routers\recommendations.py
- [[recommendations.py]] - code - Scentrix\backend\app\routers\recommendations.py
- [[search_fragrances()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[sommelier.py]] - code - Scentrix\backend\app\services\sommelier.py
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
- 11 edges to [[_COMMUNITY_Community 3]]
- 9 edges to [[_COMMUNITY_Community 1]]
- 7 edges to [[_COMMUNITY_Community 9]]
- 5 edges to [[_COMMUNITY_Community 11]]
- 4 edges to [[_COMMUNITY_Community 8]]
- 2 edges to [[_COMMUNITY_Community 0]]
- 2 edges to [[_COMMUNITY_Community 7]]
- 1 edge to [[_COMMUNITY_Community 14]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 15]]

## Top bridge nodes
- [[load_recommendation_catalog()]] - degree 17, connects to 6 communities
- [[search_fragrances()]] - degree 10, connects to 4 communities
- [[get_personalized_recommendations()]] - degree 13, connects to 3 communities
- [[rebuild_embeddings_task()]] - degree 7, connects to 3 communities
- [[_score_catalog()]] - degree 10, connects to 2 communities