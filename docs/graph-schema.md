# Fragrance Knowledge Graph Schema

## Overview

The ScentScape knowledge graph models fragrances, their olfactory characteristics, brands, user taste profiles, and relationships between fragrances based on shared notes, accords, and user co-ratings.

## Database: Neo4j 5+ (Community or AuraDB)

### Node Types

#### 1. **Fragrance**
Primary node representing a fragrance product.

**Properties:**
- `id` (String, unique) — Neo4j internal ID + external identifier
- `name` (String) — Fragrance name
- `brand_id` (String) — Reference to Brand node
- `year` (Integer) — Year of release
- `concentration` (String) — Eau de Toilette, Eau de Parfum, etc.
- `gender_label` (String) — "N/A" (neutral default), "male", "female", or custom
- `description` (String) — Long-form fragrance description (TF-IDF encoded for search)
- `created_at` (DateTime) — Ingestion timestamp
- `updated_at` (DateTime) — Last sync timestamp

**Constraints:**
```
CREATE CONSTRAINT fragrance_id_unique FOR (f:Fragrance) REQUIRE f.id IS UNIQUE
CREATE TEXT INDEX fragrance_name_ft FOR (f:Fragrance) ON f.name
```

#### 2. **Note**
Individual olfactory note (ingredient).

**Properties:**
- `id` (String, unique) — Note identifier (e.g., "bergamot", "musk")
- `name` (String) — Display name
- `category` (String) — "top", "middle", "base"
- `created_at` (DateTime)

**Constraints:**
```
CREATE CONSTRAINT note_id_unique FOR (n:Note) REQUIRE n.id IS UNIQUE
```

#### 3. **Accord**
Collection of notes that define a fragrance family.

**Properties:**
- `id` (String, unique) — Accord identifier
- `name` (String) — Accord name (e.g., "Amber", "Floral", "Woody")
- `description` (String) — Accord characteristics
- `primary_notes` (List) — Array of primary note IDs
- `created_at` (DateTime)

**Constraints:**
```
CREATE CONSTRAINT accord_id_unique FOR (a:Accord) REQUIRE a.id IS UNIQUE
```

#### 4. **Brand**
Fragrance house/brand.

**Properties:**
- `id` (String, unique) — Brand identifier
- `name` (String) — Brand name
- `country` (String) — Country of origin
- `founded_year` (Integer) — Year founded
- `website` (String, optional)
- `created_at` (DateTime)

**Constraints:**
```
CREATE CONSTRAINT brand_id_unique FOR (b:Brand) REQUIRE b.id IS UNIQUE
```

#### 5. **UserProfile**
Represents a user's taste embedding and preference vector.

**Properties:**
- `id` (String, unique) — Anonymized user ID (hash of email + salt)
- `embedding_vector_ref` (String) — Reference to Pinecone vector ID
- `last_updated` (DateTime) — When embedding was computed
- `opt_in_training` (Boolean) — GDPR: user consents to training data use
- `created_at` (DateTime)

**Constraints:**
```
CREATE CONSTRAINT user_id_unique FOR (u:UserProfile) REQUIRE u.id IS UNIQUE
```

### Edge Types (Relationships)

#### 1. **HAS_TOP_NOTE**
Fragrance → Note (top notes)

**Properties:**
- `intensity` (Float, 0.0–1.0) — Relative intensity
- `position` (Integer) — Order in top note list

#### 2. **HAS_MIDDLE_NOTE**
Fragrance → Note (heart notes)

**Properties:**
- `intensity` (Float, 0.0–1.0)
- `position` (Integer)

#### 3. **HAS_BASE_NOTE**
Fragrance → Note (base notes)

**Properties:**
- `intensity` (Float, 0.0–1.0)
- `position` (Integer)

#### 4. **BELONGS_TO_ACCORD**
Fragrance → Accord (defining accords)

**Properties:**
- `certainty` (Float, 0.0–1.0) — Confidence score
- `weight` (Float) — Relative importance in fragrance profile

#### 5. **MADE_BY**
Fragrance → Brand

**Properties:**
- None (simple relationship)

#### 6. **CO_RATED_WITH**
Fragrance → Fragrance (user co-rating similarity)

**Properties:**
- `weight` (Float, 0.0–1.0) — Co-rating frequency (users who rated both)
- `similarity_score` (Float, 0.0–1.0) — Cosine similarity of co-raters' taste vectors

#### 7. **SIMILAR_TO**
Fragrance → Fragrance (GraphSAGE embedding similarity)

**Properties:**
- `similarity_score` (Float, 0.0–1.0) — Cosine similarity in 128-dim embedding space
- `updated_at` (DateTime) — When computed
- `model_version` (String) — GraphSAGE version (e.g., "v1.0")

#### 8. **RATED_BY**
UserProfile → Fragrance (historical rating for backtracking only)

**Properties:**
- `rating_sweetness` (Float, 0.0–5.0)
- `rating_woodiness` (Float, 0.0–5.0)
- `rating_longevity` (Float, 0.0–5.0)
- `rating_projection` (Float, 0.0–5.0)
- `rating_freshness` (Float, 0.0–5.0)
- `overall_satisfaction` (Float, 0.0–5.0)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**Note:** This relationship is primarily stored in PostgreSQL; Neo4j relationship is cached.

### Query Patterns

**1. Get All Notes of a Fragrance**
```cypher
MATCH (f:Fragrance {id: $fragrance_id})-[r:HAS_TOP_NOTE|HAS_MIDDLE_NOTE|HAS_BASE_NOTE]->(n:Note)
RETURN n, r.category, r.intensity
ORDER BY r.position
```

**2. Find Similar Fragrances (GraphSAGE)**
```cypher
MATCH (f:Fragrance {id: $fragrance_id})-[sim:SIMILAR_TO]->(similar:Fragrance)
RETURN similar, sim.similarity_score
ORDER BY sim.similarity_score DESC
LIMIT 10
```

**3. Find Fragrances by Accord**
```cypher
MATCH (a:Accord {id: $accord_id})<-[r:BELONGS_TO_ACCORD]-(f:Fragrance)
RETURN f, r.weight
ORDER BY r.weight DESC
```

**4. Get User's Taste Profile (all rated fragrances)**
```cypher
MATCH (u:UserProfile {id: $user_id})-[rating:RATED_BY]->(f:Fragrance)
RETURN f, rating
```

## Data Integrity Constraints

1. **Fragrance must have at least 3 notes** (minimum 1 in each category: top, middle, base if possible)
2. **Notes must belong to valid categories** ("top", "middle", "base")
3. **No orphaned notes** (all notes must belong to at least 1 accord or fragrance)
4. **Brand references must exist** before creating fragrances
5. **Similarity scores are normalized** (0.0–1.0)
6. **GDPR compliance:** UserProfile IDs must be anonymized (salted hash of email, not plain email)

## Indexing Strategy

| Index | Type | Purpose |
|-------|------|---------|
| `fragrance_id_unique` | Unique | Primary key lookup (fast) |
| `fragrance_name_ft` | Full-Text | Text search "vanilla", "rose" |
| `note_id_unique` | Unique | Primary key lookup |
| `accord_id_unique` | Unique | Primary key lookup |
| `brand_id_unique` | Unique | Primary key lookup |
| `user_id_unique` | Unique | Anonymized user lookup |

## Size Estimates (MVP Target)

- **Fragrances:** 500–1,000
- **Notes:** 150–250
- **Accords:** 40–60
- **Brands:** 50–100
- **User Profiles:** 100–1,000 (grows with usage)
- **Edges (SIMILAR_TO):** 5,000–10,000 (post-GraphSAGE)
- **Edges (Total):** ~20,000

## Schema Evolution

- Version controlled in `schema_init.cypher`
- Backward-compatible migrations only
- Non-breaking changes: add new properties, new node types, new relationships
- Breaking changes (rare): plan for data migration script

## Security & Privacy

1. **No PII in graph:** Fragrance data only (no user names, emails, etc.)
2. **Anonymized user IDs:** Salted hash, not plaintext
3. **GDPR deletion:** On user deletion, remove all UserProfile nodes and RATED_BY edges
4. **Opt-in training:** Only use ratings from users with `opt_in_training=true` for retraining

## Performance Tuning

- Index all relationship types used in frequent queries
- Batch ingestion with `UNWIND` for bulk inserts
- Use `EXPLAIN` to validate query plans
- Profile slow queries with `PROFILE`
- Set Neo4j memory to 50% available RAM
- Connection pooling in client (py2neo)
