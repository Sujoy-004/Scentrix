# 📜 Scentrix Changelog

All notable changes to this project will be documented in this file in real-time, following the **Rewired Senior Architect** protocol.

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
