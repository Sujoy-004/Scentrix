// ScentScape Neo4j Graph Schema Initialization
// This script creates all constraints, indexes, and the graph structure
// Run this ONCE when setting up a new Neo4j instance

// ============================================================================
// FRAGRANCE NODE CONSTRAINTS & INDEXES
// ============================================================================

CREATE CONSTRAINT fragrance_id_unique IF NOT EXISTS
FOR (f:Fragrance) REQUIRE f.id IS UNIQUE;

CREATE TEXT INDEX fragrance_name_fulltext IF NOT EXISTS
FOR (f:Fragrance) ON f.name;

CREATE INDEX fragrance_created_at IF NOT EXISTS
FOR (f:Fragrance) ON f.created_at;

// ============================================================================
// NOTE NODE CONSTRAINTS & INDEXES
// ============================================================================

CREATE CONSTRAINT note_id_unique IF NOT EXISTS
FOR (n:Note) REQUIRE n.id IS UNIQUE;

CREATE INDEX note_category IF NOT EXISTS
FOR (n:Note) ON n.category;

// ============================================================================
// ACCORD NODE CONSTRAINTS & INDEXES
// ============================================================================

CREATE CONSTRAINT accord_id_unique IF NOT EXISTS
FOR (a:Accord) REQUIRE a.id IS UNIQUE;

CREATE INDEX accord_name IF NOT EXISTS
FOR (a:Accord) ON a.name;

// ============================================================================
// BRAND NODE CONSTRAINTS & INDEXES
// ============================================================================

CREATE CONSTRAINT brand_id_unique IF NOT EXISTS
FOR (b:Brand) REQUIRE b.id IS UNIQUE;

CREATE INDEX brand_name IF NOT EXISTS
FOR (b:Brand) ON b.name;

CREATE INDEX brand_country IF NOT EXISTS
FOR (b:Brand) ON b.country;

// ============================================================================
// USER PROFILE NODE CONSTRAINTS & INDEXES
// ============================================================================

CREATE CONSTRAINT userprofile_id_unique IF NOT EXISTS
FOR (u:UserProfile) REQUIRE u.id IS UNIQUE;

CREATE INDEX userprofile_created_at IF NOT EXISTS
FOR (u:UserProfile) ON u.created_at;

CREATE INDEX userprofile_opt_in IF NOT EXISTS
FOR (u:UserProfile) ON u.opt_in_training;

// ============================================================================
// RELATIONSHIP INDEXES
// ============================================================================

// SIMILAR_TO relationships (used in recommendation queries)
CREATE INDEX similar_to_fragrance IF NOT EXISTS
FOR ()-[r:SIMILAR_TO]-() ON r.similarity_score;

// CO_RATED_WITH relationships (collaborative filtering)
CREATE INDEX co_rated_with IF NOT EXISTS
FOR ()-[r:CO_RATED_WITH]-() ON r.weight;

// RATED_BY relationships (user history)
CREATE INDEX rated_by IF NOT EXISTS
FOR ()-[r:RATED_BY]-() ON r.created_at;

// ============================================================================
// SCHEMA METADATA (Version tracking)
// ============================================================================

CREATE CONSTRAINT schema_version_unique IF NOT EXISTS
FOR (s:SchemaVersion) REQUIRE s.version IS UNIQUE;

// Record schema initialization
MERGE (sv:SchemaVersion {version: "1.0"})
SET sv.created_at = datetime(),
    sv.description = "Initial ScentScape graph schema",
    sv.notes = [
      "Fragrance node: id, name, brand_id, year, concentration, gender_label, description",
      "Note node: id, name, category (top/middle/base)",
      "Accord node: id, name, description, primary_notes",
      "Brand node: id, name, country, founded_year",
      "UserProfile node: id, embedding_vector_ref, last_updated, opt_in_training",
      "Relationships: HAS_TOP_NOTE, HAS_MIDDLE_NOTE, HAS_BASE_NOTE, BELONGS_TO_ACCORD, MADE_BY, CO_RATED_WITH, SIMILAR_TO, RATED_BY"
    ];

// ============================================================================
// SCHEMA VERIFICATION QUERY
// ============================================================================

// Run this to verify all constraints and indexes are created:
// SHOW CONSTRAINTS;
// SHOW INDEXES;
