# 🧠 Scentrix Sovereignty Matrix (Context Linkage)

## 🛡️ Session Context: 2026-04-28
This session resolved the "Data Rot" crisis and established a singular, authoritative Single Source of Truth (SSOT).

### 🏛️ Dataset Sovereignty
- **Primary SSOT**: `ml/data/scentrix_master.json`
- **Total Records**: 4,577 (The "Sovereign 5k" Elite Pool)
- **ID Schema**: `frag_{brand}_{name}_{year}` (Globally unique slug)
- **Selection Criteria**: `rating_count > 500` (Enforced for 512MB RAM deployment readiness).
- **Deduplication Logic**: 672 collisions resolved; redundant files `fra_elite_24k.json` and `fra_cleaned_canonical.json` have been purged.

### ⚙️ Infrastructure Stability
- **Dependency**: `psutil` is now a mandatory dependency in `pyproject.toml`.
- **Environment**: Local `.venv` is fully synced with `runtime` and `ml` extras.
- **Render Readiness**: System is optimized to run within 512MB RAM by utilizing the shrunken 5k dataset and lazy-loading embeddings.

### 🔮 Next Steps (Semantic Enrichment)
- **Current State**: Descriptions are 100% template-based ("A sophisticated...").
- **Goal**: Apply "Aethera" atmospheric narratives to the top 50 fragrances as a pilot.

## 🕸️ Neural Connectivity
- **Neo4j**: Connected via `scentrix_master.json`.
- **Pinecone**: Synchronized with `scentrix_master.json` IDs.
- **Hybrid Search**: Tuned for the 4.5k pool.

---
*This file serves as the "Architect's Memory" for context restoration in future turns.*
