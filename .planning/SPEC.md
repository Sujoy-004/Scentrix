# 📝 SPEC.md: Scentrix Production Recovery & UI Hardening

**Status:** APPROVED (In Progress)
**Persona:** Rewired Senior Architect
**Goal:** Restore production connectivity and resolve high-friction UI papercuts.

---

## 1. Objectives

### Phase 1: Backend Recovery (Priority: CRITICAL)
- **Diagnostic**: Confirm the cause of `NXDOMAIN` for `scentrix-api.up.railway.app`.
- **Infrastructure**: Verify Railway deployment status and domain configuration.
- **Verification**: Ensure the API is reachable and returning a 200 OK on `/api/health`.

### Phase 2: Local Verification Gate (Priority: HIGH)
- **Command**: Run `make up` to synchronize the local environment.
- **Parity**: Verify that the backend logic (Graph + Vector) functions correctly in isolation.
- **Test**: Execute `make test-backend` to ensure no regression in the neural discovery flow.

### Phase 3: Frontend Hardening (Priority: MEDIUM)
- **Asset Fix**: Add/restore `favicon.ico` to the `frontend/public` directory.
- **UX Fix**: Update `Navbar.tsx` search portal to trigger on icon-click in addition to `Enter` key.
- **Cleanup**: Investigate and remove/fix the non-functional Hero search element identified in the audit.

---

## 2. Technical Requirements

- **API URL**: If the Railway domain has changed, update `NEXT_PUBLIC_API_URL` in the production environment (Vercel/Railway) and verify `backend/app/services/vault.py` integrity.
- **Diagnostics**: Technical error messages (e.g., "Neural link lost") must remain diagnostic per USER directive.
- **Logging**: Every finding and change MUST be logged in `CHANGELOG.md` in real-time.

---

## 3. Nyquist Verification Gates (Success Criteria)

1. [ ] **Gate 1**: `https://scentrix-api.up.railway.app/api/health` (or new domain) returns `{"status": "healthy"}`.
2. [ ] **Gate 2**: Local `make test-backend` returns 100% pass rate.
3. [ ] **Gate 3**: Discovery quiz on `scentrix-one.vercel.app` successfully starts a session without "Neural link lost" error.
4. [ ] **Gate 4**: `favicon.ico` renders correctly in the browser tab.

---

## 4. Constraint Checklist
- [x] Strict Typing (No `any`).
- [x] PII Encryption (DataVault).
- [x] GSD Wave Architecture.
- [x] real-time CHANGELOG updates.
