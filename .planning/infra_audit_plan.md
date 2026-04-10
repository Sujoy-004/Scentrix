# Scentrix INFRA-AUDIT: ELITE 24k RECOVERY PLAN

**OBJECTIVE:** Stabilize the "Quiet Luxury" discovery engine for 24,063 Elite records. Resolve Neo4j OOM risks, align 384D GNN/Text embeddings, and baseline performance for cinematic fluidity.

---

## 🟢 PHASE 1: SYSTEM AUDIT & BASELINING
- [x] **A.1: Cardinality Audit** — Count all nodes/relationships/labels to identify scaling hotspots. [7.4M edges detected!]
- [x] **A.1.x: DUPLICATE PURGE** — Execute relationship de-duplication for `BELONGS_TO_ACCORD` and `HAS_NOTE`. [355k final edges!]
- [x] **A.2: Memory Profiling** — Test peak memory usage for complex `MATCH` queries. [FAILED: 45s vs 300ms SLA!]
- [ ] **A.3: Vector Parity Check** — Verify Pinecone index vs. Neo4j ID synchronization. [10,600 / 24,063 Complete]
- [ ] **A.3: Vector Parity Check** — Verify Pinecone index vs. Neo4j ID synchronization.

## 🟡 PHASE 2: RESILIENCE & SCALING
- [x] **S.1: Relationship Indexing** — Create constraint/index for `Note.name` and `Accord.name`.
- [ ] **S.1.x: ADAPTIVE DISCOVERY** — Pivot from Full-Graph Search to **Vector-First Selection**. Graph-only used for reranking.
- [ ] **S.2: Memory Optimization** — Adjust Neo4j `dbms.memory.transaction.total.max` or implement strict batching in API routers.
- [ ] **S.3: Embedding Up-sampling** — Upgrade `GraphSAGE` architecture from 128D to 384D for unified vector fusion.

## 🔵 PHASE 3: SEMANTIC RERANKING & SECURITY (INTEL)
- [ ] **I.0: PII VAULT** — Implement UUID-only mapping in GNN nodes. Delegate PII/Ratings to encrypted PG instance (AES-256).
- [ ] **I.1: Hybrid Logic Ingest** — Implement Reciprocal Rank Fusion (RRF) at the service layer (Hugging Face target).
- [ ] **I.2: Weight Tuning** — Balance Text Similarity vs. Graph Genetics (Target: 70/30 split).
- [ ] **I.3: Social Proof Integration** — Expose `review_sample` metadata in search results to mask synthesis latency.

## 🔴 PHASE 4: QUIET LUXURY PERFORMANCE (UX)
- [ ] **U.1: Throughput Benchmark** — Load test 10 concurrent discovery grid requests.
- [ ] **U.2: Video Scrubber Handover** — Ensure Next.js hydration doesn't block background video playback on high-CPU searches.
- [ ] **U.3: Final Lock** — Commit stable infra-config and purge recovery scripts.

---

## 🛠️ REAL-TIME PROGRESS LOG
- **2026-04-08 00:18**: Plan created. Commencing Phase 1.
- **2026-04-08 00:52**: [A.1 COMPLETE] Card audit revealed systemic relationship leak (7.4M identical edges).
- **2026-04-08 00:55**: [A.1.x COMPLETE] Pruned 9M redundancy -> 355k optimized edges. Memory stabilized.
- **2026-04-08 00:58**: [A.2 COMPLETE] SLA CRITICALLY BREACHED. 45s discovery query detected. Moving to Adaptive Search.
- **2026-04-08 01:28**: [A.3 PARTIAL] 10,600/24,063 vectors synced to Pinecone. 
- **2026-04-08 01:31**: [I.0 PARTIAL] DataVault implemented. User model updated with RBAC & Encryption fields.
- [PENDING]: S.1.x Adaptive Discovery Logic.
