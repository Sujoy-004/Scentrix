# Scentrix Changelog

---

## SYSTEM STATE (CURRENT)

Status: PARTIALLY WORKING

Backend:
- Local server runs successfully (`uvicorn app.main:app`)
- `/fragrances` → working
- `/recommendations/guest` → working
- ML recommendation engine producing real scores

Frontend:
- Runs locally
- Connected to backend (after CORS fix)
- `/fragrances` route loads
- Data fetch works

Critical Issues:
- UI not matching expected “wow” design
- FragranceCard not rendering as intended
- Data → UI mismatch still present
- No clear separation of catalog vs recommendation display
- No stable production-ready flow

---

## PHASE 0 — DEBUG BASELINE (DONE)

- Fixed wrong uvicorn entrypoint
- Backend boot verified
- DB connection verified
- Recommendation engine verified
- Swagger tested
- CORS issue fixed
- Frontend successfully connected to local backend

---

## PHASE 1 — CORE ARCHITECTURE LOCK (DONE)

- Backend structure confirmed:
  - routers/
  - services/
  - schemas/
  - models/
- Frontend structure confirmed:
  - app/
  - components/
  - lib/

- Confirmed key routes:
  - `/fragrances` → catalog
  - `/recommendations/guest` → inference

---

## PHASE 2 — MAJOR PROBLEM IDENTIFIED

Root issue:

Frontend UI expects:
- rich data (images, ratings, notes)

Backend provides:
- minimal data (no images, empty notes, null ratings)

Result:
- UI looks “broken” but actually data is incomplete

---

## PHASE 3 — FIX STRATEGY (IN PROGRESS)

### 3.1 Data Layer Fix
Goal:
- Normalize backend output to match UI expectations

Actions:
- Add fallback for:
  - `top_notes ← top_accords`
  - `rating ← default or computed`
  - `image_url ← placeholder or mapping`

---

### 3.2 UI Integration Fix
Goal:
- Restore original premium UI

Rules:
- DO NOT rewrite `FragranceCard`
- DO NOT use raw `<div>` UI
- ONLY adapt data passed to component

---

### 3.3 Routing Fix
Goal:
Clear separation:

- `/fragrances` → public catalog
- `/collection` → private wishlist

---

### 3.4 Recommendation Flow Fix
Goal:
- Show recommendations inside UI properly

Tasks:
- Add frontend call to:
  - `/recommendations/guest`
- Render results using same `FragranceCard`

---

## PHASE 4 — FRONTEND STABILIZATION (PENDING)

Tasks:

- Fix FragranceCard rendering mismatch
- Ensure props match expected structure (`frag`)
- Restore:
  - animations
  - hover effects
  - visual density

---

## PHASE 5 — BACKEND ENHANCEMENT (PENDING)

Tasks:

- Add richer metadata:
  - images
  - ratings
  - notes
- Improve recommendation explanation (`reason`)
- Ensure consistent schema across all endpoints

---

## PHASE 6 — FULL SYSTEM INTEGRATION (PENDING)

Goal:
Single flow works end-to-end:

1. User lands on homepage
2. Clicks "Browse Library"
3. Sees catalog (`/fragrances`)
4. Takes quiz / inputs preferences
5. Gets recommendations
6. Saves to collection

---

## PHASE 7 — DEPLOYMENT HARDENING (PENDING)

- Ensure Vercel frontend build stable
- Ensure backend API stable (Render/local)
- Fix environment variables
- Ensure no CORS issues in production

---

## PHASE 8 — FINAL QUALITY CHECK (PENDING)

Checklist:

- No broken routes
- No redirect loops
- No “failed to fetch”
- UI consistent everywhere
- Recommendations feel meaningful

---

## FINAL TARGET

System is complete when:

- Local works ✅
- Production works ✅
- UI looks premium ✅
- Recommendations are personalized ✅
- No manual hacks required ✅

---

## CURRENT FOCUS

→ Fix UI rendering mismatch  
→ Align backend data with frontend expectations  
→ Restore FragranceCard full capability

---

## RULES (NON-NEGOTIABLE)

- No rewriting working components
- No blind refactoring
- No guessing API schema
- Always verify via backend response
- Always fix root cause, not symptoms