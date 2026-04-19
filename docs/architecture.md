# Target Architecture

The current implementation is still transitioning, but the target production
stack is:

User -> Vercel frontend -> FastAPI on Railway -> Supabase for auth/profile/
preference data only -> background workers and caches -> Pinecone and Neo4j for
derived recommendation work.

## Data ownership

- Vercel hosts the customer-facing Next.js app and should stay thin.
- FastAPI on Railway owns orchestration, API contracts, and request shaping.
- Supabase is the source of truth for identity, profile, preferences, consent,
  and deletion requests.
- Redis and Celery handle async jobs, warmups, and short-lived caches.
- Pinecone and Neo4j store derived recommendation state, not user-owned source
  records.

## Why this split works

- It shortens the critical request path for the user.
- It keeps user-owned data in one place, which simplifies deletion and consent.
- It lets recommendation search stay derived and cacheable instead of making
  every request hit the graph/vector layer directly.
- It reduces the chance of split-brain state between profile data and the
  recommendation engine.

## Practical rule

If a record belongs to the user, it should live in Supabase. If a record is an
embedding, graph edge, score, or recommendation artifact, it should live in the
derived stores or cache layer.