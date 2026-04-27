---
source_file: "Scentrix\ml\flows\weekly_refresh.py"
type: "code"
community: "Community 0"
location: "L250"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_0
---

# weekly_fragrance_etl()

## Connections
- [[.get()]] - `calls` [INFERRED]
- [[Main ETL workflow.          Scheduled to run weekly on Sundays at 200 AM UTC.]] - `rationale_for` [EXTRACTED]
- [[RuntimeError]] - `calls` [INFERRED]
- [[clean_fragrances()]] - `calls` [EXTRACTED]
- [[ingest_to_neo4j()]] - `calls` [EXTRACTED]
- [[scrape_fragrances()]] - `calls` [EXTRACTED]
- [[validate_graph()]] - `calls` [EXTRACTED]
- [[weekly_refresh.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_0