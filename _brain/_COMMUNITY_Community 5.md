---
type: community
members: 53
---

# Community 5

**Members:** 53 nodes

## Members
- [[.__init__()_18]] - code - Scentrix\ml\tests\test_graph.py
- [[.execute_query()]] - code - Scentrix\ml\graph\neo4j_client.py
- [[.validate_accord_count()]] - code - Scentrix\ml\tests\test_graph.py
- [[.validate_brand_count()]] - code - Scentrix\ml\tests\test_graph.py
- [[.validate_data_quality()]] - code - Scentrix\ml\tests\test_graph.py
- [[.validate_fragrance_count()]] - code - Scentrix\ml\tests\test_graph.py
- [[.validate_fragrance_note_coverage()]] - code - Scentrix\ml\tests\test_graph.py
- [[.validate_fragrance_relationships()]] - code - Scentrix\ml\tests\test_graph.py
- [[.validate_note_categories()]] - code - Scentrix\ml\tests\test_graph.py
- [[.validate_note_count()]] - code - Scentrix\ml\tests\test_graph.py
- [[.validate_orphaned_accords()]] - code - Scentrix\ml\tests\test_graph.py
- [[.validate_orphaned_notes()]] - code - Scentrix\ml\tests\test_graph.py
- [[Check for orphaned accords.          Returns             Result dict]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Check for orphaned notes (not connected to any fragrance).          Returns]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Check overall data quality metrics.          Returns             Result dict]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Execute a query and return results.          Args             query Cypher]] - rationale - Scentrix\ml\graph\neo4j_client.py
- [[Fragrance search result.]] - rationale - Scentrix\backend\app\schemas\schemas.py
- [[FragranceSearchResult]] - code - Scentrix\backend\app\schemas\schemas.py
- [[Get fragrance detail including notes, accords, and similarity to user profile.]] - rationale - Scentrix\backend\app\routers\fragrances.py
- [[Graph validation tests for Scentrix.  Validates Neo4j graph integrity and data]] - rationale - Scentrix\ml\tests\test_graph.py
- [[GraphValidator]] - code - Scentrix\ml\tests\test_graph.py
- [[Initialize validator.          Args             neo4j_client Neo4j client i]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Lazy initialize neo4j client]] - rationale - Scentrix\backend\app\routers\fragrances.py
- [[List fragrances with lightweight pagination and optional brand filter.]] - rationale - Scentrix\backend\app\routers\fragrances.py
- [[Return a 7-day recommendation quality dashboard for the current user.]] - rationale - Scentrix\backend\app\routers\fragrances.py
- [[Search fragrances by name, brand, or accord.]] - rationale - Scentrix\backend\app\routers\fragrances.py
- [[Standalone function to validate graph.      Args         neo4j_client Neo4j]] - rationale - Scentrix\ml\tests\test_graph.py
- [[T2.4 Fragrance search and recommendation endpoints.  Provides endpoints for]] - rationale - Scentrix\backend\app\routers\fragrances.py
- [[Threshold bundle for a validation environment.]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Validate all fragrances have notes in all categories.          Returns]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Validate fragrances have minimum relationships.          Returns]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Validate minimum accord count.          Returns             Result dict]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Validate minimum brand count.          Returns             Result dict]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Validate minimum fragrance count.          Returns             Result dict]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Validate minimum note count.          Returns             Result dict]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Validate note categories are valid.          Returns             Result dict]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Validates fragrance knowledge graph integrity.]] - rationale - Scentrix\ml\tests\test_graph.py
- [[ValidationProfile]] - code - Scentrix\ml\tests\test_graph.py
- [[_catalog_filtered_rows()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[_catalog_filtered_rows_from_list()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[_env_bool()]] - code - Scentrix\ml\tests\test_graph.py
- [[_matches_text()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[_parse_context_json()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[_safe_pct()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[fragrances.py]] - code - Scentrix\backend\app\routers\fragrances.py
- [[get_catalog()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[get_fragrance_detail()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[get_graph_client()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[get_recommendation_weekly_metrics()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[list_fragrances()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[search_fragrances()]] - code - Scentrix\backend\app\routers\fragrances.py
- [[test_graph.py]] - code - Scentrix\ml\tests\test_graph.py
- [[validate_graph()_1]] - code - Scentrix\ml\tests\test_graph.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_5
SORT file.name ASC
```

## Connections to other communities
- 17 edges to [[_COMMUNITY_Community 0]]
- 10 edges to [[_COMMUNITY_Community 1]]
- 4 edges to [[_COMMUNITY_Community 4]]
- 4 edges to [[_COMMUNITY_Community 3]]
- 3 edges to [[_COMMUNITY_Community 14]]
- 1 edge to [[_COMMUNITY_Community 6]]
- 1 edge to [[_COMMUNITY_Community 12]]

## Top bridge nodes
- [[fragrances.py]] - degree 17, connects to 3 communities
- [[get_catalog()]] - degree 6, connects to 3 communities
- [[.execute_query()]] - degree 20, connects to 2 communities
- [[get_fragrance_detail()]] - degree 11, connects to 2 communities
- [[search_fragrances()]] - degree 10, connects to 2 communities