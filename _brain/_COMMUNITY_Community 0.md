---
type: community
members: 128
---

# Community 0

**Members:** 128 nodes

## Members
- [[.__init__()_11]] - code - Scentrix\ml\pipeline\clean.py
- [[.__init__()_12]] - code - Scentrix\ml\pipeline\ingest.py
- [[._build_graph()]] - code - Scentrix\ml\models\graph_sage.py
- [[._clean_fragrance()]] - code - Scentrix\ml\pipeline\clean.py
- [[._ingest_accord()]] - code - Scentrix\ml\pipeline\ingest.py
- [[._ingest_fragrance()]] - code - Scentrix\ml\pipeline\ingest.py
- [[._ingest_note()]] - code - Scentrix\ml\pipeline\ingest.py
- [[._normalize_notes()]] - code - Scentrix\ml\pipeline\clean.py
- [[._validate_accords()]] - code - Scentrix\ml\pipeline\clean.py
- [[._validate_required_fields()]] - code - Scentrix\ml\pipeline\clean.py
- [[.clean_fragrance_list()]] - code - Scentrix\ml\pipeline\clean.py
- [[.get()]] - code - Scentrix\backend\app\cache.py
- [[.ingest_fragrances()]] - code - Scentrix\ml\pipeline\ingest.py
- [[.load_and_clean()]] - code - Scentrix\ml\pipeline\clean.py
- [[.load_and_ingest()]] - code - Scentrix\ml\pipeline\ingest.py
- [[.report()]] - code - Scentrix\ml\pipeline\clean.py
- [[.save_cleaned()]] - code - Scentrix\ml\pipeline\clean.py
- [[.set()]] - code - Scentrix\backend\app\cache.py
- [[.validate_all()]] - code - Scentrix\ml\tests\test_graph.py
- [[Adaptive quiz session endpoints.  Scaffolds a confidence-aware onboarding quiz]] - rationale - Scentrix\backend\app\routers\quiz.py
- [[Bridge transient quiz session data to permanent profile table.]] - rationale - Scentrix\backend\app\routers\quiz.py
- [[Build PyTorch Geometric graph data from seed JSON.]] - rationale - Scentrix\ml\models\graph_sage.py
- [[Clean individual fragrance record.          Args             frag Raw fragr]] - rationale - Scentrix\ml\pipeline\clean.py
- [[Clean list of fragrance records.          Args             fragrances Raw f]] - rationale - Scentrix\ml\pipeline\clean.py
- [[Cleans and validates fragrance data from raw scrapi or seed sources.]] - rationale - Scentrix\ml\pipeline\clean.py
- [[Close global Neo4j client.]] - rationale - Scentrix\ml\graph\neo4j_client.py
- [[Data cleaning pipeline for Scentrix.  Validates raw fragrance data, deduplicat]] - rationale - Scentrix\ml\pipeline\clean.py
- [[Filters the fragrance dataset by performance metrics.]] - rationale - Scentrix\ml\pipeline\filter_elite.py
- [[FragranceDataCleaner]] - code - Scentrix\ml\pipeline\clean.py
- [[FragranceGraphIngestor]] - code - Scentrix\ml\pipeline\ingest.py
- [[Get cleaning statistics.          Returns             Stats dict]] - rationale - Scentrix\ml\pipeline\clean.py
- [[Ingest accord and create relationship.          Args             frag_id Fr]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Ingest fragrance list into Neo4j.          Idempotent uses MERGE to avoid dup]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Ingest single fragrance record.          Steps         1. Createupdate Bran]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Ingest single note and create relationship.          Args             frag_i]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Ingests cleaned fragrance data into Neo4j graph.]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Initialize cleaner.          Args             strict_mode If True, reject r]] - rationale - Scentrix\ml\pipeline\clean.py
- [[Initialize global Neo4j client.      Args         uri Neo4j URI         us]] - rationale - Scentrix\ml\graph\neo4j_client.py
- [[Initialize ingestor.          Args             neo4j_client Neo4j client in]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Integrates CSV dataset into the Scentrix neural format.]] - rationale - Scentrix\scripts\normalize_dataset.py
- [[Load JSON file and clean fragrances.          Args             filepath Pat]] - rationale - Scentrix\ml\pipeline\clean.py
- [[Load cleaned JSON and ingest into Neo4j.          Args             filepath]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Main ETL workflow.          Scheduled to run weekly on Sundays at 200 AM UTC.]] - rationale - Scentrix\ml\flows\weekly_refresh.py
- [[Neo4j graph ingestion for fragrance data.  Loads cleaned fragrance records int]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Normalize note names.          Args             notes Raw note list]] - rationale - Scentrix\ml\pipeline\clean.py
- [[Olfactive Diversity Audit for Scentrix. Analyzes the distribution of fragrances]] - rationale - Scentrix\ml\pipeline\diversity_audit.py
- [[Persist integration output as JSON artifact for release audits.]] - rationale - Scentrix\ml\tests\test_integration.py
- [[Pretty-print test results.]] - rationale - Scentrix\ml\tests\test_integration.py
- [[Quiz session store — Redis-backed with in-memory fallback.  If Redis is unavai]] - rationale - Scentrix\backend\app\services\quiz_store.py
- [[QuizSessionRules]] - code - Scentrix\backend\app\schemas\schemas.py
- [[Return a live Redis client or None if Redis is unavailable.]] - rationale - Scentrix\backend\app\services\quiz_store.py
- [[Run all validation checks.          Returns             Results dict with va]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Run complete integration test of data pipeline.          Args         seed_d]] - rationale - Scentrix\ml\tests\test_integration.py
- [[Save cleaned fragrances to JSON.          Args             fragrances Clean]] - rationale - Scentrix\ml\pipeline\clean.py
- [[Server-side adaptive quiz stopping rules.]] - rationale - Scentrix\backend\app\schemas\schemas.py
- [[Standalone function to clean fragrance JSON file.      Args         input_pa]] - rationale - Scentrix\ml\pipeline\clean.py
- [[Standalone function to ingest fragrances.      Args         neo4j_client Ne]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Summarize validation results into passfailerror buckets.]] - rationale - Scentrix\ml\tests\test_graph.py
- [[T1.10 Prefect workflow for weekly ETL pipeline.  Orchestrates the complete fr]] - rationale - Scentrix\ml\flows\weekly_refresh.py
- [[T1.12 Integration test for complete Phase 1 data pipeline.  Tests the full en]] - rationale - Scentrix\ml\tests\test_integration.py
- [[Task Clean and normalize fragrance data.          Args         raw_data_pat]] - rationale - Scentrix\ml\flows\weekly_refresh.py
- [[Task Ingest cleaned fragrances into Neo4j.          Args         cleaned_da]] - rationale - Scentrix\ml\flows\weekly_refresh.py
- [[Task Scrape Fragrantica for new fragrances.          Args         days_back]] - rationale - Scentrix\ml\flows\weekly_refresh.py
- [[Task Validate graph integrity after ingestion.          Args         neo4j_]] - rationale - Scentrix\ml\flows\weekly_refresh.py
- [[Test health check endpoint.]] - rationale - Scentrix\backend\tests\test_health.py
- [[Test version endpoint.]] - rationale - Scentrix\backend\tests\test_health.py
- [[Validate and normalize accords.          Args             accords Raw accor]] - rationale - Scentrix\ml\pipeline\clean.py
- [[Validate required fields are present.          Args             frag Fragra]] - rationale - Scentrix\ml\pipeline\clean.py
- [[_build_confidence_components()]] - code - Scentrix\backend\app\routers\quiz.py
- [[_compute_confidence_score()]] - code - Scentrix\backend\app\routers\quiz.py
- [[_confidence_band()]] - code - Scentrix\backend\app\routers\quiz.py
- [[_get_redis()]] - code - Scentrix\backend\app\services\quiz_store.py
- [[_load_seen_ids()]] - code - Scentrix\backend\app\routers\quiz.py
- [[_normalize_rating_0_to_5()]] - code - Scentrix\backend\app\routers\quiz.py
- [[_question_from_row()]] - code - Scentrix\backend\app\routers\quiz.py
- [[_quiz_key()]] - code - Scentrix\backend\app\services\quiz_store.py
- [[_require_owned_session()]] - code - Scentrix\backend\app\routers\quiz.py
- [[_safe_float()]] - code - Scentrix\backend\app\routers\quiz.py
- [[_select_seed_questions()]] - code - Scentrix\backend\app\routers\quiz.py
- [[_to_rules_payload()]] - code - Scentrix\backend\app\routers\quiz.py
- [[_write_integration_report()]] - code - Scentrix\ml\tests\test_integration.py
- [[audit_dataset()]] - code - Scentrix\ml\pipeline\diversity_audit.py
- [[clean.py]] - code - Scentrix\ml\pipeline\clean.py
- [[clean_fragrance_file()]] - code - Scentrix\ml\pipeline\clean.py
- [[clean_fragrances()]] - code - Scentrix\ml\flows\weekly_refresh.py
- [[close_neo4j()]] - code - Scentrix\ml\graph\neo4j_client.py
- [[create_quiz_session()]] - code - Scentrix\backend\app\services\quiz_store.py
- [[diversity_audit.py_1]] - code - Scentrix\ml\pipeline\diversity_audit.py
- [[evaluate_quiz_session()]] - code - Scentrix\backend\app\routers\quiz.py
- [[fetchFeed()]] - code - Scentrix\frontend\src\app\internal\overseer\page.tsx
- [[filter_elite.py]] - code - Scentrix\ml\pipeline\filter_elite.py
- [[filter_elite_dataset()]] - code - Scentrix\ml\pipeline\filter_elite.py
- [[finalize_quiz_session()]] - code - Scentrix\backend\app\routers\quiz.py
- [[get_next_quiz_questions()]] - code - Scentrix\backend\app\routers\quiz.py
- [[get_quiz_session()]] - code - Scentrix\backend\app\services\quiz_store.py
- [[ingest.py]] - code - Scentrix\ml\pipeline\ingest.py
- [[ingest_fragrances_from_file()]] - code - Scentrix\ml\pipeline\ingest.py
- [[ingest_to_neo4j()]] - code - Scentrix\ml\flows\weekly_refresh.py
- [[init_neo4j()]] - code - Scentrix\ml\graph\neo4j_client.py
- [[load()]] - code - Scentrix\frontend\src\app\fragrances\page.tsx
- [[load_data()]] - code - Scentrix\backend\scripts\full_ingest_24k.py
- [[main()_2]] - code - Scentrix\backend\scripts\seed_data.py
- [[middleware()]] - code - Scentrix\frontend\middleware.ts
- [[middleware.ts]] - code - Scentrix\frontend\middleware.ts
- [[normalize_csv_to_json()]] - code - Scentrix\scripts\normalize_dataset.py
- [[normalize_dataset.py]] - code - Scentrix\scripts\normalize_dataset.py
- [[page.tsx_6]] - code - Scentrix\frontend\src\app\families\[family]\page.tsx
- [[page.tsx_7]] - code - Scentrix\frontend\src\app\fragrances\page.tsx
- [[page.tsx_9]] - code - Scentrix\frontend\src\app\internal\overseer\page.tsx
- [[print_results()]] - code - Scentrix\ml\tests\test_integration.py
- [[quiz.py]] - code - Scentrix\backend\app\routers\quiz.py
- [[quiz_expiry_utc()]] - code - Scentrix\backend\app\services\quiz_store.py
- [[quiz_store.py]] - code - Scentrix\backend\app\services\quiz_store.py
- [[run_integration_test()]] - code - Scentrix\ml\tests\test_integration.py
- [[save_quiz_session()]] - code - Scentrix\backend\app\services\quiz_store.py
- [[scrape_fragrances()]] - code - Scentrix\ml\flows\weekly_refresh.py
- [[seed_data.py]] - code - Scentrix\backend\scripts\seed_data.py
- [[start_quiz_session()]] - code - Scentrix\backend\app\routers\quiz.py
- [[submit_quiz_answer()]] - code - Scentrix\backend\app\routers\quiz.py
- [[summarize_validation_results()]] - code - Scentrix\ml\tests\test_graph.py
- [[test_health.py]] - code - Scentrix\backend\tests\test_health.py
- [[test_health_check()]] - code - Scentrix\backend\tests\test_health.py
- [[test_integration.py_1]] - code - Scentrix\ml\tests\test_integration.py
- [[test_root()]] - code - Scentrix\backend\tests\test_health.py
- [[test_version()]] - code - Scentrix\backend\tests\test_health.py
- [[validate_graph()]] - code - Scentrix\ml\flows\weekly_refresh.py
- [[weekly_fragrance_etl()]] - code - Scentrix\ml\flows\weekly_refresh.py
- [[weekly_refresh.py]] - code - Scentrix\ml\flows\weekly_refresh.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_0
SORT file.name ASC
```

## Connections to other communities
- 25 edges to [[_COMMUNITY_Community 3]]
- 19 edges to [[_COMMUNITY_Community 4]]
- 17 edges to [[_COMMUNITY_Community 5]]
- 11 edges to [[_COMMUNITY_Community 2]]
- 10 edges to [[_COMMUNITY_Community 7]]
- 9 edges to [[_COMMUNITY_Community 1]]
- 9 edges to [[_COMMUNITY_Community 11]]
- 7 edges to [[_COMMUNITY_Community 13]]
- 7 edges to [[_COMMUNITY_Community 8]]
- 5 edges to [[_COMMUNITY_Community 18]]
- 3 edges to [[_COMMUNITY_Community 21]]
- 3 edges to [[_COMMUNITY_Community 23]]
- 2 edges to [[_COMMUNITY_Community 14]]
- 2 edges to [[_COMMUNITY_Community 24]]
- 1 edge to [[_COMMUNITY_Community 36]]
- 1 edge to [[_COMMUNITY_Community 26]]
- 1 edge to [[_COMMUNITY_Community 16]]
- 1 edge to [[_COMMUNITY_Community 9]]
- 1 edge to [[_COMMUNITY_Community 38]]
- 1 edge to [[_COMMUNITY_Community 17]]
- 1 edge to [[_COMMUNITY_Community 15]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 6]]

## Top bridge nodes
- [[.get()]] - degree 120, connects to 22 communities
- [[.set()]] - degree 20, connects to 5 communities
- [[run_integration_test()]] - degree 19, connects to 2 communities
- [[load()]] - degree 11, connects to 2 communities
- [[evaluate_quiz_session()]] - degree 11, connects to 2 communities