# 📜 Scentrix Changelog

All notable changes to this project will be documented in this file in real-time, following the **Rewired Senior Architect** protocol.

## [2026-04-29] - Roadmap & Strategy Expansion
- [DOCS] **Roadmap**: Expanded the "Future Work" section in `README.md` to include technical specifications for Feedback Loops, Evaluation Metrics (CTR, Top-K), and State-aware Personalization.

## [2026-04-29] - Documentation & Maintenance
- [DOCS] **README**: Created production-grade `README.md` with detailed architecture, performance metrics, and design decisions.
- [DOCS] **Author Info**: Synchronized author details and GitHub links.

## [2026-04-29] - Production Deployment (Render + Vercel)
- [INFRA] **Backend Live**: Deployed `scentrix-backend-prod` to Render.
- [INFRA] **Frontend Connected**: Updated Vercel environment variables (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_API_BASE_URL`) to point to Render.
- [DEPLOY] **Verification**: Confirmed `/health` (200 OK) and successful quiz session initialization.
- [DATA] **SSOT Verification**: Confirmed 4,577 records loaded from `scentrix_master.json`.
- [STATUS] **End-to-End Operational**: Frontend-to-Backend neural link established.

## [2026-04-30] - API Contract Hardening & Determinism (Production Grade)
- [API] **StandardResponse V2**: Updated global response wrapper to include `code` and `message` for production-grade error reporting.
- [API] **Global Error Consistency**: Standardized `main.py` exception handlers to enforce the new structured error format across the entire API.
- [API] **DB-Aware Stability**: Added proactive database availability checks to all `auth` and `users` endpoints, returning `503 Service Unavailable` instead of crashing when infra is offline.
- [QUIZ] **HybridRecommender Upgrade**: Integrated precomputed semantic embeddings (15% weight) with average user profile vectorization.
- [QUIZ] **Latency Hardening**: Optimized scoring loop with aggressive candidate pruning and pre-normalized NumPy dot-product similarity (Average Latency: ~44ms).
- [QUIZ] **Production Hygiene**: Cleaned repository of temporary scripts, updated `.gitignore`, and stabilized dependencies (NumPy < 2.0).
- [QUIZ] **Deployment Ready**: Verified 100% success across core endpoints and edge case fallbacks.
- [QUIZ] **Intra-Session Determinism**: Enforced same-input-same-output behavior in the quiz engine by seeding random sampling with the `session_id`.
- [QUIZ] **Seed Coverage**: Updated `_select_seed_questions` to ensure variety while maintaining determinism via passed-through RNG.
- [API] **Health Check Hardening**: Updated `GET /health` to return the `StandardResponse` format for consistency.

## [2026-04-28] - Scentrix Dataset Sovereignty Hardening
- [DATA] **Unified Master SSOT**: Established `ml/data/scentrix_master.json` as the singular authoritative source of truth.
- [DATA] **Deduplication**: Resolved 672 ID collisions using the `frag_{brand}_{name}_{year}` schema.
- [DATA] **Sovereign 5k Optimization**: Shrunk dataset from 21k to **4,577 elite items** (rating_count > 500) to hit 512MB RAM target for Render Free Tier.
- [INFRA] **Dependency Hardening**: Added `psutil` to `pyproject.toml` and synchronized the local `.venv` with all ML/Runtime dependencies.
- [ML] **Codebase Synchronization**: Updated `Makefile`, `seed_data.py`, `catalog.py`, `graph_sage.py`, and `diversity_audit.py` to point exclusively to the new Master SSOT.
- [ML] **Memory Optimization**: Updated `hybrid_search.py` with lazy-loading and RAM-aware warmup logic.
- [CLEANUP] **Legacy Purge**: Permanently deleted `fra_elite_24k.json` and `fra_cleaned_canonical.json`.

## [2026-04-27] - Render Migration & Configuration Hardening
- [INFRA] Render Readiness: Created `backend/requirements.txt` and purged Railway-specific `railway.json` and `Procfile`.
- [CONFIG] Environment Lockdown: Enforced strict `DATABASE_URL`, `JWT_SECRET_KEY`, and `DATA_ENCRYPTION_KEY` requirement with no fallbacks.
- [API] Health Check: Standardized `GET /health` to flat `{"status": "ok"}` for Render compatibility.
- [DATA] Path Optimization: Fixed ML dataset pathing in `catalog.py` to correctly traverse from `backend/app/services` to project root.
- [AUTH] Protocol Synchronization: Activated **Rewired Senior Architect** persona (Mythos-GSD-Graphify).
- [CONTEXT] Codebase Ingestion: Completed deep read of `SOVEREIGNTY.md`, `README.md`, `AGENTS.md`, and `CHANGELOG.md`.
- [GRAPH] Brain Synchronization: Verified `_brain` and `graphify-out/graph.json` structural integrity for neural context linkage.
- [STATUS] Scentrix Neural Engine synchronized. Initialized and standing by for Socratic Specification.

## [2026-04-27] - Global Error Handling & API Standardization
- [API] Unified Response Format: Converted all remaining manual error returns in routers (especially `recommendations.py`) to `raise HTTPException`, relying on the global handler for formatting.
- [ML] Deterministic ML Readiness: Enforced `503 Service Unavailable` with a clear initialization message when the Neural Engine or Embeddings cache is not ready.
- [ML] Strict Path Enforcement: Removed all heuristic (note-overlap) and trending fallbacks. The system now strictly follows the `Quiz → Embeddings → Similarity → Response` path.
- [CLEANUP] Python Standardization: Replaced all legacy `null` literals with Python `None` and fixed code duplication in `auth.py`.

## [2026-04-27] - Global API Contract & Safety Enforcement
- [API] Global Response Contract: Enforced unified `{status, data, error}` format across ALL routers (`auth`, `users`, `leads`, `quiz`, `fragrances`, `recommendations`).
- [API] Type Hint Unification: Standardized all router function signatures to `-> StandardResponse` for documentation and validation consistency.
- [SECURITY] Decryption Safety: Hardened `auth.py` and `users.py` to handle decryption failures gracefully without leaking sensitive details.
- [INFRA] Validation Format: Verified `main.py` global handlers correctly intercept `HTTPException` and generic `Exception` into the standard contract.

## [2026-04-27] - System Stabilization & Response Standardization
- [SECURITY] Hardened Decryption: All `DataVault.decrypt` calls now wrapped in safety blocks with proper fallbacks.
- [INFRA] Fail-Fast Configuration: Validated that `config.py` correctly raises errors at startup if critical secrets are missing.
- [API] Standardized Responses: Updated `/leads/capture`, `/leads/feed`, `/users/ratings`, and `/users/saved` to use a consistent `{status, data}` JSON structure.

## [2026-04-27] - Production Hardening & Security Fixes
- [SECURITY] Env Hardening: `JWT_SECRET_KEY` and `DATA_ENCRYPTION_KEY` no longer have default values; system fails fast if missing.
- [SECURITY] Encryption Safety: Updated `decrypt` to raise `ValueError` on failure instead of returning raw input.
- [SECURITY] PII Logging Removal: Removed raw email logging in `auth.py` to prevent PII exposure in logs.
- [AUTH] JWT Performance: Fixed double-decode issue in `dependencies.py`; payload is now decoded once and passed through.
- [TIME] Temporal Consistency: Global migration from `datetime.utcnow()` to `datetime.now(UTC)` for future-proofing.

## [2026-04-27] - Backend Production Audit
- Completed a strict backend audit covering `auth/`, `routers/`, `schemas/`, and `database.py`.
- Identified critical security risks (default keys, decryption leakage, PII logging).
- Flagged inconsistent response formats and missing Pydantic strictness.
