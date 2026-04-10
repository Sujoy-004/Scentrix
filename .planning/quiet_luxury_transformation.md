# Scentrix: "Quiet Luxury" Full-Stack Transformation

The infrastructure audit and core data-layer fixes are complete. We are now executing the visual and structural transformation to meet the "Quiet Luxury" production standards.

## 1. Core Logic Fixes (COMPLETED)
- [X] **Graph Hydration Fix**: Refactored `catalog.py` to aggregate notes/accords via relationships.
- [X] **Asynchronous Warmup**: Decoupled Neural Engine encoding (24,063 items) from HTTP server boot for instant responsiveness.
- [X] **Filter Integrity**: 'Amber' and 'Rose' filtering now verified across 24k records (Neo4j scale).

## 2. Frontend: Cinematic UI Overhaul
### A. Discovery Grid (`/fragrances/page.tsx`)
- [ ] **Glassmorphic Cards**: Implement `backdrop-filter: blur(12px)` and deconstructed border gradients.
- [ ] **Dynamic Backgrounds**: Integrate `VideoScrubber` for scroll-linked atmosphere switching based on selected family.
- [ ] **Olfactive Gauges**: Replace static scores with SVG-based neural resonance indicators.

### B. Genetic Profile (`/fragrances/[id]/page.tsx`)
- [ ] **Video Atmosphere**: Inject `VideoScrubber` as a deep-layered background for each fragrance's profile.
- [ ] **Genetic Neighbors**: Implement a "Molecular Similarity" carousel using the hybrid search service.
- [ ] **Deconstructed Typography**: Shift to high-contrast *Cormorant Garamond* for titles with absolute-positioned label tags.

### C. System Polish
- [ ] **Favicon**: Deploy high-fidelity gold/noir Scentrix icon.
- [ ] **Handoff Animation**: Ensure smooth Framer Motion transitions between catalog and detail views.

## 3. Implementation Workflow
1.  **Stage 1**: Update `globals.css` with premium design tokens.
2.  **Stage 2**: Implement cinematic `VideoScrubber` on Detail pages.
3.  **Stage 3**: Refactor Catalog Grid for "Quiet Luxury" aesthetic.
4.  **Stage 4**: Verify 300ms SLA and visual parity via browser subagent.
