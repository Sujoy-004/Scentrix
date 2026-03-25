# PHASE 5.7 EXECUTION PLAN: Performance & Accessibility Hardening

**Status:** Ready for Launch  
**Branch:** `phase/5-hardening` (maintain existing)  
**GSD Phase:** Final Validation Layer  
**Estimated Duration:** 1-2 weeks  
**Model Allocation:** Haiku (visual regression), Sonnet (A11y), Flash (Lighthouse)

---

## PHASE 5.7 OBJECTIVES

Phase 5.7 focuses on **visual regression testing, performance benchmarking, and accessibility compliance** — the final validation gates before production readiness.

### Primary Deliverables

| Deliverable | Type | Success Metric |
|-------------|------|----------------|
| Visual Regression Test Suite | Code | 100+ snapshots captured |
| Lighthouse Baseline Report | Report | ≥85 across all categories |
| WCAG 2.1 AA Audit Report | Audit | 0 critical issues |
| Performance Optimization Recs | Doc | 5+ actionable items |
| Advanced Coverage Report | Metrics | ≥75% code coverage |

---

## TASK BREAKDOWN: PHASE 5.7

### 5.7.1 Visual Regression Testing Setup ✅ READY

**Objective:** Establish visual baseline for all 11 pages across 3 breakpoints.

**Tasks:**
1. Initialize Playwright visual comparison API
2. Capture baseline snapshots for:
   - Desktop (1280px)
   - Tablet (768px)
   - Mobile (375px)
3. Create visual regression tests for:
   - Each page in /11-pages structure
   - Light/dark mode toggle (if applicable)
   - Responsive breakpoints
4. Set up CI integration (GitHub Actions)
5. Document snapshot review workflow

**Acceptance Criteria:**
- ✅ 30+ baseline snapshots captured (11 pages × 3 breakpoints)
- ✅ 0 baseline failures
- ✅ CI pipeline green
- ✅ Missing snapshots flagged in logs

**Time Estimate:** 4-6 hours

**Model:** `claude-haiku-4` (mechanical snapshot setup)

---

### 5.7.2 Lighthouse Performance Audit ✅ READY

**Objective:** Benchmark performance cores and identify optimization opportunities.

**Tasks:**
1. Configure Lighthouse CI (optional: self-hosted or use Lighthouse GitHub Action)
2. Run against Vercel preview deployment:
   - Home page
   - Quiz page
   - Recommendations page
   - Login/Register pages
3. Capture baseline scores across:
   - Performance (target: ≥85)
   - Accessibility (target: ≥90)
   - Best Practices (target: ≥90)
   - SEO (target: ≥90)
4. Identify Top 5 optimization opportunities:
   - Image optimization
   - JavaScript bundle size
   - CSS splitting
   - Font loading strategy
   - Caching headers
5. Document recommendations with priority

**Acceptance Criteria:**
- ✅ All 4 pages audited
- ✅ Baseline scores recorded
- ✅ 5+ optimization recs documented
- ✅ Priority levels assigned (P1-P3)
- ✅ Report generated (JSON + markdown)

**Time Estimate:** 5-7 hours

**Model:** `gemini-2.5-flash` (visual performance analysis)

---

### 5.7.3 WCAG 2.1 AA Accessibility Audit ✅ READY

**Objective:** Ensure WCAG 2.1 AA compliance across entire frontend.

**Tasks:**
1. Install automated testing tools:
   - axe-core (accessibility checks)
   - Playwright's accessibility API
   - WAVE Browser Extension (manual validation)
2. Automated checks (axe-core):
   - Color contrast
   - ARIA attributes
   - Semantic HTML
   - Form labeling
   - Keyboard navigation
3. Manual accessibility tests:
   - Screen reader testing (NVDA/JAWS simulation)
   - Keyboard-only navigation
   - Focus management
   - Motion/animation sensitivity
4. Create accessibility test suite (Playwright)
5. Document compliance report and remediation plan

**Acceptance Criteria:**
- ✅ 0 critical accessibility violations
- ✅ 0-3 minor warnings (documented)
- ✅ Keyboard navigation verified
- ✅ Screen reader compatibility confirmed
- ✅ WCAG 2.1 AA report signed off

**Time Estimate:** 6-8 hours

**Model:** `claude-sonnet-4` (detailed A11y analysis)

---

### 5.7.4 Coverage Analysis & Optimization ✅ READY

**Objective:** Increase test coverage from 60-70% to ≥75%.

**Tasks:**
1. Generate coverage report from existing 44 tests
2. Identify untested code paths in:
   - Components (RatingSlider, NotePyramid, etc.)
   - Utils & hooks
   - State management (Zustand stores)
3. Add 5-10 new targeted tests:
   - Edge cases
   - Error boundaries
   - State transitions
4. Document coverage by module:
   - Components: target ≥80%
   - Pages: target ≥70%
   - Utils: target ≥85%
5. Update coverage badge in README

**Acceptance Criteria:**
- ✅ Overall coverage ≥75%
- ✅ 5+ new tests added
- ✅ Critical paths covered
- ✅ Coverage report published
- ✅ README updated with badge

**Time Estimate:** 4-5 hours

**Model:** `claude-haiku-4` (coverage analysis)

---

### 5.7.5 Performance Optimization Implementation ✅ READY

**Objective:** Implement top optimization opportunities identified in 5.7.2.

**Sample Optimizations (if needed):**

1. **Image Optimization**
   - Convert to WebP format
   - Responsive image sizing
   - Lazy loading for below-fold

2. **Bundle Size Reduction**
   - Tree-shake unused dependencies
   - Code splitting for pages
   - Dynamic imports for heavy charts (D3, recharts)

3. **Font Loading**
   - Preload critical fonts
   - Font-display: swap
   - Subset Unicode range

4. **CSS Optimization**
   - Purge unused Tailwind classes
   - Critical CSS inline
   - Defer non-critical CSS

5. **Caching Strategy**
   - Set appropriate Cache-Control headers
   - Service Worker for offline support (optional Phase 5.8)

**Acceptance Criteria:**
- ✅ ≥3 optimizations implemented
- ✅ Lighthouse score improvement quantified
- ✅ No functionality regressions
- ✅ All 44 tests passing post-optimization
- ✅ Before/after metrics documented

**Time Estimate:** 6-8 hours

**Model:** `gemini-2.5-flash` (optimization implementation)

---

### 5.7.6 Final Validation & Gate Review ✅ READY

**Objective:** Verify all Phase 5.7 success criteria met; authorize Phase 5.8.

**Tasks:**
1. Review all reports:
   - Visual regression baseline ✅
   - Lighthouse scores ✅
   - WCAG 2.1 AA compliance ✅
   - Coverage metrics ✅
   - Optimization results ✅
2. Merge phase/5-hardening into develop
3. Run full test suite:
   - 44 E2E tests
   - Coverage report
   - Lint check
   - TypeScript check
4. Generate Phase 5.7 Completion Report
5. Update progress.json
6. Authorize Phase 5.8 or Phase 6

**Acceptance Criteria:**
- ✅ All reports delivered
- ✅ All tests passing (44/44)
- ✅ Git history clean
- ✅ Documentation complete
- ✅ Sign-off obtained
- ✅ Zero blockers for Phase 5.8

**Time Estimate:** 2-3 hours

**Model:** `claude-haiku-4` (checklist validation)

---

## RESOURCE ALLOCATION

### Model Routing for Phase 5.7

| Task | Model | Justification | Hours |
|------|-------|---------------|-------|
| Visual Regression | `claude-haiku-4` | Mechanical snapshot API | 4-6 |
| Lighthouse Audit | `gemini-2.5-flash` | Visual performance analysis | 5-7 |
| A11y Audit | `claude-sonnet-4` | Detailed SAP analysis | 6-8 |
| Coverage Analysis | `claude-haiku-4` | Metrics parsing | 4-5 |
| Optimization | `gemini-2.5-flash` | Codegen + perf tuning | 6-8 |
| Validation | `claude-haiku-4` | Final checklist | 2-3 |
| **Total** | — | — | **27-37 hours** |

**Token Budget:** ~45,000 tokens (across all tasks)

---

## SUCCESS CRITERIA MATRIX

| Criterion | Target | Measurement | Must-Have |
|-----------|--------|-------------|-----------|
| Lighthouse Performance | ≥85 | Light House audit | ✅ |
| Lighthouse Accessibility | ≥90 | Lighthouse audit | ✅ |
| Lighthouse Best Practices | ≥90 | Lighthouse audit | ✅ |
| Lighthouse SEO | ≥90 | Lighthouse audit | ✅ |
| WCAG 2.1 AA | 0 critical | Axe-core + manual | ✅ |
| Visual Regression | All captured | 30+ snapshots | ✅ |
| Test Coverage | ≥75% | Coverage report | ✅ |
| E2E Tests | 44/44 passing | npm run test:e2e | ✅ |
| Build | <3s | npm run build | ✅ |
| Lint | 0 errors | npm run lint | ✅ |
| TypeScript | 0 errors | npx tsc --noEmit | ✅ |

**Gate Status:** 🟢 **CLEAR TO LAUNCH**

---

## EXECUTION SEQUENCE

### Day 1-2: Visual Regression & Performance
1. Set up Playwright visual comparison (Task 5.7.1)
2. Capture 30+ baseline snapshots
3. Run Lighthouse audit (Task 5.7.2)
4. Identify optimization opportunities

### Day 3: Accessibility
1. Set up axe-core integration (Task 5.7.3)
2. Run automated accessibility checks
3. Manual keyboard navigation testing
4. Document findings

### Day 4-5: Optimization & Testing
1. Implement top 3-5 optimizations (Task 5.7.5)
2. Validate all tests pass
3. Re-run Lighthouse (measure improvement)
4. Coverage analysis (Task 5.7.4)

### Day 6: Final Validation
1. Complete Phase 5.7 Completion Report (Task 5.7.6)
2. Merge to develop
3. Git tag: `v0.5.7-rc1`
4. Authorize Phase 5.8

---

## DELIVERABLE CHECKLIST

- [ ] Visual Regression Test Suite (`tests/visual-regression/`)
- [ ] Visual Regression Report (`reports/visual-baseline.json`)
- [ ] Lighthouse Baseline Report (`reports/lighthouse-baseline.html`)
- [ ] WCAG 2.1 AA Audit Report (`reports/a11y-audit.md`)
- [ ] Performance Optimization Document (`docs/5.7-optimization-recommendations.md`)
- [ ] Coverage Report (`reports/coverage/`)
- [ ] Phase 5.7 Completion Report (`PHASE_5.7_COMPLETION.md`)
- [ ] Updated README with metrics badges
- [ ] Updated progress.json

---

## KNOWLEDGE BASE

### Key Files to Reference

- [Playwright Snapshots](https://playwright.dev/docs/test-snapshots)
- [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci)
- [axe Accessibility Testing](https://www.deque.com/axe/devtools/)
- [WCAG 2.1 AA Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

### Tools Pre-Installed

- ✅ Playwright (already configured)
- ✅ @testing-library/react (assertions)
- Need to install: `@axe-core/playwright`, `lighthouse`, `axe-playwright`

---

## RISK MITIGATION

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Low Lighthouse scores | High | Document tradeoffs, prioritize optimizations |
| A11y critical issues | High | Use Sonnet model for deep analysis; manual testing |
| Visual regression false positives | Medium | Review baseline carefully; pixel-perfect not required |
| Coverage gaps in complex components | Medium | Prioritize user-facing flows; document edge cases |
| Build degradation | High | Run full test suite after each optimization |

---

## HAND-OFF TO PHASE 5.8

**Phase 5.8 (Future) Will Include:**
- Service Worker & offline support
- Advanced caching strategies
- SEO optimization (meta tags, structured data)
- Analytics integration (optional)
- Beta user testing coordination

**Pre-Conditions for Phase 5.8:**
- ✅ Phase 5.7 complete & validated
- ✅ All Lighthouse scores ≥85
- ✅ WCAG 2.1 AA compliance
- ✅ Test coverage ≥75%

---

## COMMAND REFERENCE

```bash
# Phase 5.7 Primary Commands

# 5.7.1 Visual Regression
npx playwright test --update-snapshots
npx playwright test --headed  # review captures

# 5.7.2 Lighthouse Audit
npm install -g lighthouse
lighthouse https://scentscape.vercel.app --view
# Or use: lhci autorun

# 5.7.3 Accessibility Testing
npm install -D @axe-core/playwright
npx playwright test  # (with axe checks integrated)

# 5.7.4 Coverage Report
npm run test:coverage
open coverage/index.html

# 5.7.5 Full Validation
npm run lint
npx tsc --noEmit
npm run build
npm run test:e2e
npm run test:coverage
```

---

## NEXT STEPS

**Immediate (Now):**
1. ✅ Distribute this plan to team
2. ✅ Confirm resource allocation
3. ✅ Create phase/5-hardening branch (already exists)
4. ✅ Begin Task 5.7.1 (Visual Regression)

**Upon Completion:**
1. Merge phase/5-hardening → develop
2. Create GitHub release notes
3. Plan Phase 5.8 or Phase 6 transition
4. Coordinate with stakeholders on performance roadmap

---

**Plan Version:** 1.0  
**Created:** March 25, 2026  
**Status:** 🟢 READY FOR EXECUTION  
**Authorization:** ✅ APPROVED TO PROCEED

