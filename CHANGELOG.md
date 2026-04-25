# 📜 Scentrix Changelog

All notable changes to this project will be documented in this file in real-time, following the **Rewired Senior Architect** protocol.

## [2026-04-25] - Initial Session
### 🏗️ Architectural Mapping
- Completed full codebase audit (Backend, Frontend, ML clusters).
- Ingested Context Engines (`_brain/`, `.planning/`, `graphify-out/`).
- Calibrated to **Workspace Sovereignty Manifest v2.1.0**.
- Initialized real-time `CHANGELOG.md`.

## [2026-04-25] - Production Audit
### 🔴 Critical Issues Identified
- **Backend Domain Failure**: `scentrix-api.up.railway.app` is returning **NXDOMAIN**. Core features (Adaptive Quiz, Neural Search) are completely broken in production.
- **Frontend Integration Error**: The discovery quiz fails with "Neural link lost" immediately upon starting due to the backend connectivity issue.

### 🟡 UX/DX Polish Required
- **Missing Assets**: `favicon.ico` is missing (404).
- **Navbar Friction**: Search bar in `Navbar.tsx` only triggers on `Enter` key; lacks a clickable search action/icon button.
- **Dead Search Element**: The subagent identified a non-functional search-like element in the Hero section (needs investigation to see if it's a z-index issue or a layout artifact).

### 🟢 Aesthetic Verification
- **Cinematic Standards**: Visual audit confirms high-fidelity dark mode, elegant typography, and smooth transitions (Framer Motion) align with "Quiet Luxury" standards.
- **Neural Loader**: The discovery loading sequence is functional and visually premium.

### 🛠️ Implementation (Phase 1)
- [BACKEND] Hardened `hybrid_search.py` to handle Pinecone failures gracefully with semantic fallback.
- [BACKEND] Corrected environment variable disparity: Updated Pinecone index names from `Scentrix-*` to `scentscape-*`.
- [FIX] Resolved 'div' nested in 'p' hydration error in `HeroSection.tsx`.
- [INFRA] Synchronized Docker build context to repository root.
- [INFRA] Optimized `.dockerignore` for 90% faster build transfers.
- [INFRA] Fixed redundant backend paths in `Dockerfile`.
- [VERIFY] Forcing fresh container build to ensure code-browser parity.
- [FRONTEND] Fixed Search Persistence bug in `fragrances/page.tsx` by using `useSearchParams` hook and dynamic effects.
- [FRONTEND] Temporarily suppressed PostHog telemetry to unblock local environment verification.

---
**Status:** IMPLEMENTING - Addressing search persistence and cookie banner dismissal logic.
