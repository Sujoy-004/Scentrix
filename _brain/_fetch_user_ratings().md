---
source_file: "Scentrix\backend\app\tasks\recommend_tasks.py"
type: "code"
community: "Community 7"
location: "L230"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_7
---

# _fetch_user_ratings()

## Connections
- [[.close()_1]] - `calls` [INFERRED]
- [[.run()]] - `calls` [INFERRED]
- [[Load user ratings in Celery context while tolerating unavailable DB dependencies]] - `rationale_for` [EXTRACTED]
- [[_fetch_user_ratings_async()]] - `calls` [EXTRACTED]
- [[generate_user_embeddings_task()]] - `calls` [EXTRACTED]
- [[recommend_by_profile_task()]] - `calls` [EXTRACTED]
- [[recommend_by_text_task()]] - `calls` [EXTRACTED]
- [[recommend_tasks.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_7