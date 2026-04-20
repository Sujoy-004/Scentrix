---
type: community
members: 79
---

# Community 0

**Members:** 79 nodes

## Members
- [[.__init__()_11]] - code - Scentrix\ml\pipeline\ingest.py
- [[.__init__()_17]] - code - Scentrix\ml\tests\test_graph.py
- [[._ingest_accord()]] - code - Scentrix\ml\pipeline\ingest.py
- [[._ingest_fragrance()]] - code - Scentrix\ml\pipeline\ingest.py
- [[._ingest_note()]] - code - Scentrix\ml\pipeline\ingest.py
- [[.execute_query()]] - code - Scentrix\ml\graph\neo4j_client.py
- [[.ingest_fragrances()]] - code - Scentrix\ml\pipeline\ingest.py
- [[.load_and_ingest()]] - code - Scentrix\ml\pipeline\ingest.py
- [[.validate_accord_count()]] - code - Scentrix\ml\tests\test_graph.py
- [[.validate_all()]] - code - Scentrix\ml\tests\test_graph.py
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
- [[Close global Neo4j client.]] - rationale - Scentrix\ml\graph\neo4j_client.py
- [[Execute a query and return results.          Args             query Cypher]] - rationale - Scentrix\ml\graph\neo4j_client.py
- [[FragranceGraphIngestor]] - code - Scentrix\ml\pipeline\ingest.py
- [[Graph validation tests for Scentrix.  Validates Neo4j graph integrity and da]] - rationale - Scentrix\ml\tests\test_graph.py
- [[GraphValidator]] - code - Scentrix\ml\tests\test_graph.py
- [[Ingest accord and create relationship.          Args             frag_id Fr]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Ingest fragrance list into Neo4j.          Idempotent uses MERGE to avoid dup]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Ingest single fragrance record.          Steps         1. Createupdate Bran]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Ingest single note and create relationship.          Args             frag_i]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Ingests cleaned fragrance data into Neo4j graph.]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Initialize global Neo4j client.      Args         uri Neo4j URI         us]] - rationale - Scentrix\ml\graph\neo4j_client.py
- [[Initialize ingestor.          Args             neo4j_client Neo4j client in]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Initialize validator.          Args             neo4j_client Neo4j client i]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Load cleaned JSON and ingest into Neo4j.          Args             filepath]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Main ETL workflow.          Scheduled to run weekly on Sundays at 200 AM UTC.]] - rationale - Scentrix\ml\flows\weekly_refresh.py
- [[Neo4j graph ingestion for fragrance data.  Loads cleaned fragrance records int]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Persist integration output as JSON artifact for release audits.]] - rationale - Scentrix\ml\tests\test_integration.py
- [[Pretty-print test results.]] - rationale - Scentrix\ml\tests\test_integration.py
- [[Run all validation checks.          Returns             Results dict with va]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Run complete integration test of data pipeline.          Args         seed_d]] - rationale - Scentrix\ml\tests\test_integration.py
- [[Standalone function to ingest fragrances.      Args         neo4j_client Ne]] - rationale - Scentrix\ml\pipeline\ingest.py
- [[Standalone function to validate graph.      Args         neo4j_client Neo4j]] - rationale - Scentrix\ml\tests\test_graph.py
- [[Summarize validation results into passfailerror buckets.]] - rationale - Scentrix\ml\tests\test_graph.py
- [[T1.10 Prefect workflow for weekly ETL pipeline.  Orchestrates the complete fr]] - rationale - Scentrix\ml\flows\weekly_refresh.py
- [[T1.12 Integration test for complete Phase 1 data pipeline.  Tests the full en]] - rationale - Scentrix\ml\tests\test_integration.py
- [[Task Ingest cleaned fragrances into Neo4j.          Args         cleaned_da]] - rationale - Scentrix\ml\flows\weekly_refresh.py
- [[Task Scrape Fragrantica for new fragrances.          Args         days_back]] - rationale - Scentrix\ml\flows\weekly_refresh.py
- [[Task Validate graph integrity after ingestion.          Args         neo4j_]] - rationale - Scentrix\ml\flows\weekly_refresh.py
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
- [[_env_bool()]] - code - Scentrix\ml\tests\test_graph.py
- [[_write_integration_report()]] - code - Scentrix\ml\tests\test_integration.py
- [[close_neo4j()]] - code - Scentrix\ml\graph\neo4j_client.py
- [[ingest.py]] - code - Scentrix\ml\pipeline\ingest.py
- [[ingest_fragrances_from_file()]] - code - Scentrix\ml\pipeline\ingest.py
- [[ingest_to_neo4j()]] - code - Scentrix\ml\flows\weekly_refresh.py
- [[init_neo4j()]] - code - Scentrix\ml\graph\neo4j_client.py
- [[main()_2]] - code - Scentrix\backend\scripts\seed_data.py
- [[print_results()]] - code - Scentrix\ml\tests\test_integration.py
- [[run_integration_test()]] - code - Scentrix\ml\tests\test_integration.py
- [[scrape_fragrances()]] - code - Scentrix\ml\flows\weekly_refresh.py
- [[seed_data.py]] - code - Scentrix\backend\scripts\seed_data.py
- [[summarize_validation_results()]] - code - Scentrix\ml\tests\test_graph.py
- [[test_graph.py]] - code - Scentrix\ml\tests\test_graph.py
- [[test_integration.py_1]] - code - Scentrix\ml\tests\test_integration.py
- [[validate_graph()_1]] - code - Scentrix\ml\tests\test_graph.py
- [[validate_graph()]] - code - Scentrix\ml\flows\weekly_refresh.py
- [[weekly_fragrance_etl()]] - code - Scentrix\ml\flows\weekly_refresh.py
- [[weekly_refresh.py]] - code - Scentrix\ml\flows\weekly_refresh.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_0
SORT file.name ASC
```

## Connections to other communities
- 11 edges to [[_COMMUNITY_Community 3]]
- 10 edges to [[_COMMUNITY_Community 8]]
- 5 edges to [[_COMMUNITY_Community 5]]
- 3 edges to [[_COMMUNITY_Community 14]]
- 3 edges to [[_COMMUNITY_Community 10]]
- 2 edges to [[_COMMUNITY_Community 11]]
- 2 edges to [[_COMMUNITY_Community 4]]
- 1 edge to [[_COMMUNITY_Community 1]]

## Top bridge nodes
- [[.execute_query()]] - degree 20, connects to 5 communities
- [[run_integration_test()]] - degree 19, connects to 5 communities
- [[weekly_fragrance_etl()]] - degree 8, connects to 3 communities
- [[ingest_to_neo4j()]] - degree 9, connects to 2 communities
- [[init_neo4j()]] - degree 8, connects to 2 communities