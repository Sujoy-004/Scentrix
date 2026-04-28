# Scentrix Brain: API Contract Hardening & Determinism

## Date: 2026-04-30
## Scope: Backend (Production Stability)

---

### 1. Unified Response Protocol (StandardResponse V2)
- **Problem**: Inconsistent error formats and success structures made frontend integration fragile.
- **Solution**: Hardened `StandardResponse` schema to enforce:
  - `status`: Always "success" or "error".
  - `data`: Payload (can be null for errors).
  - `code`: Explicit HTTP status code for better client-side routing.
  - `message`: Human-readable description (crucial for error debugging).
- **Implementation**: Updated `main.py` global exception handlers to intercept all `HTTPException` and generic `Exception` calls, ensuring 100% contract compliance.

### 2. Infrastructure-Aware Resilience
- **Problem**: Backend crashes when DB or ML dependencies are missing in restricted environments (e.g., Render Free Tier).
- **Solution**: 
  - All database-dependent endpoints (`auth`, `users`, `leads`) now perform a proactive `session` check.
  - If the database is unreachable, they return a structured `503 Service Unavailable` response instead of a 500 Internal Server Error.
  - This allows the frontend to show "Maintenance" or "Limited Mode" UI rather than blank pages.

### 3. Quiz Engine Determinism
- **Problem**: Random sampling of questions led to non-reproducible quiz sessions, making debugging and user-resumption difficult.
- **Solution**: 
  - Seeding the `random.Random` instance with the `session_id`.
  - Moved `session_id` generation to the start of the `/start` logic to ensure all subsequent sampling/shuffling is deterministic for that specific session.
  - Passed the RNG instance down to `_select_seed_questions` to maintain the "Kingdom Coverage" variety while keeping it repeatable for the same session.

### 4. System Integrity
- **Health Check**: Standardized `GET /health` to return the `StandardResponse` format, ensuring consistent monitoring logs.
- **Edge Cases**: Verified that empty input ratings and invalid IDs are handled gracefully through the centralized validation and DB-availability logic.
