# RALPH LOOP EXECUTION GUIDE — Phase 5.7

**Version:** 2.0 (Clean-Context Iteration)  
**Phase:** 5.7 (Performance & Accessibility Hardening)  
**Status:** 🟢 READY FOR EXECUTION

---

## QUICK START

### Prerequisites
```powershell
# 1. Navigate to project
cd "C:\Users\KIIT0001\Downloads\Telegram Desktop\ScentScapeAI\ScentScape"

# 2. Verify git branch
git status  # Should show: On branch phase/5-hardening

# 3. Verify progress.json exists
Test-Path ./progress.json  # Should return: True
```

### Launch Ralph Loop Automation

**Option 1: Dry Run (Preview what will execute)**
```powershell
& ".\ralph-loop.ps1" -Phase "5.7" -MaxIterations 50 -DryRun
```

**Option 2: Live Execution (Execute tasks and commit)**
```powershell
& ".\ralph-loop.ps1" -Phase "5.7" -MaxIterations 50
```

---

## WHAT RALPH LOOP DOES

1. **Reads current state** from `progress.json`
2. **Gets next incomplete task** from `RALPH_LOOP_PHASE_5.7_CHECKLIST.md`
3. **Executes task** (runs tests, builds, validates)
4. **Commits result** with message: `[phase-5.7] task-ID: description`
5. **Updates progress.json** with completion status
6. **Loops** until all tasks done or a blocker is hit
7. **Logs everything** to timestamped log file

---

## MANUAL TASK EXECUTION (If Not Using Ralph Loop)

### Task 5.7.1: Visual Regression Testing

**Objective:** Capture baseline visual snapshots for all 11 pages × 3 breakpoints = 30 snapshots

#### Step 1: Start Dev Server
```bash
cd frontend
npm run dev
# Wait for: "✓ ready - started server on 0.0.0.0:3000"
```

#### Step 2: Capture Baselines
**In a new terminal:**
```bash
cd "C:\Users\KIIT0001\Downloads\Telegram Desktop\ScentScapeAI\ScentScape\frontend"
npx playwright test tests/visual-regression.spec.ts --update-snapshots
```

#### Step 3: Verify Snapshots
```bash
ls tests/__snapshots__/
# Expected: ~30 PNG files (~5-10MB total)
```

#### Step 4: View HTML Report
```bash
npx playwright show-report
```

#### Step 5: Commit Results
```bash
cd ..  # Back to project root
git add frontend/tests/__snapshots__ frontend/tests/visual-regression.spec.ts
git commit -m "[phase-5.7] task-5.7.1: Visual regression baseline captured"
```

---

### Task 5.7.2: Lighthouse Performance Audit

**Objective:** Benchmark performance and identify optimizations

#### Step 1: Install Lighthouse CLI
```bash
cd frontend
npm install -D lighthouse@latest
```

#### Step 2: Deploy Frontend (or use Vercel preview)
- Ensure frontend is deployed to: `https://scentscape.vercel.app`
- OR run local: `npm run build && npm run dev`

#### Step 3: Run Lighthouse Audits
```bash
npx lighthouse https://scentscape.vercel.app \
  --output=html \
  --output-path=../reports/lighthouse-home.html
  
npx lighthouse https://scentscape.vercel.app/onboarding/quiz \
  --output=html \
  --output-path=../reports/lighthouse-quiz.html
  
# Repeat for: /recommendations, /auth/login, /auth/register
```

#### Step 4: Analyze and Document
```bash
# Open HTML reports in browser
openbrowser reports/lighthouse-home.html
openbrowser reports/lighthouse-quiz.html
# ... etc
```

#### Step 5: Commit Results
```bash
git add reports/lighthouse-*.html docs/5.7-optimization-recommendations.md
git commit -m "[phase-5.7] task-5.7.2: Lighthouse baseline audit complete"
```

---

### Task 5.7.3: WCAG 2.1 AA Accessibility Audit

**Objective:** Ensure WCAG 2.1 AA compliance

#### Step 1: Install Accessibility Tools
```bash
cd frontend
npm install -D @axe-core/playwright axe-playwright
```

#### Step 2: Create A11y Test (if needed)
```bash
# Tests are already defined in:
# tests/accessibility.spec.ts (to be created in subtask 5.7.3.2)
```

#### Step 3: Run Accessibility Tests
```bash
npx playwright test tests/accessibility.spec.ts
```

#### Step 4: Document Findings
```bash
# Create: WCAG_2.1_AA_AUDIT.md
# Include: Test results, violations, remediation plan
```

#### Step 5: Commit Results
```bash
git add tests/accessibility.spec.ts reports/WCAG_2.1_AA_AUDIT.md
git commit -m "[phase-5.7] task-5.7.3: WCAG 2.1 AA compliance verified"
```

---

### Task 5.7.4: Code Coverage Analysis

**Objective:** Improve coverage from 60-70% to ≥75%

#### Step 1: Generate Coverage Report
```bash
cd frontend
npm run test:coverage
# Opens: coverage/index.html
```

#### Step 2: Identify Gaps
```bash
# Review: coverage/index.html
# Note uncovered: Components, Pages, Utils (by %)
```

#### Step 3: Write New Tests
```bash
# Add 5-10 tests to:
# tests/e2e/additional-coverage.spec.ts
```

#### Step 4: Re-check Coverage
```bash
npm run test:coverage
# Verify: ≥75% coverage
```

#### Step 5: Commit Results
```bash
git add tests/e2e/additional-coverage.spec.ts coverage/
git commit -m "[phase-5.7] task-5.7.4: Code coverage improved to 75%"
```

---

### Task 5.7.5: Performance Optimization

**Objective:** Implement 3-5 optimizations to improve Lighthouse scores

#### Based on Task 5.7.2 Findings, Implement:

**Example Optimizations:**

1. Image Optimization (WebP conversion)
   ```bash
   # Convert PNG/JPG to WebP
   # Update <Image> tags with fallbacks
   ```

2. Code Splitting (Heavy libraries)
   ```typescript
   // In components that use D3, Recharts:
   const Chart = dynamic(() => import('@/components/Chart'), {
     loading: () => <Skeleton />,
   });
   ```

3. Font Loading
   ```tsx
   // In app/layout.tsx:
   <link rel="preload" href="/fonts/..." as="font" type="font/woff2" />
   ```

4. CSS Purging
   ```ts
   // Verify Tailwind config content paths are correct
   ```

#### Step 1: Benchmark Baseline (from Task 5.7.2)
- Record Lighthouse score: **___ /100**

#### Step 2: Implement Optimization 1
- Commit each optimization separately

#### Step 3: Re-run Lighthouse
- Measure improvement: **+___ points**

#### Step 4: Compile Results
- Document before/after metrics

#### Step 5: Commit Results
```bash
git add .
git commit -m "[phase-5.7] task-5.7.5: Applied performance optimizations"
```

---

### Task 5.7.6: Final Validation & Merge

**Objective:** Validate all Phase 5.7 success criteria and merge

#### Step 1: Run Full Test Suite
```bash
npm run lint
npx tsc --noEmit
npm run build
npm run test:e2e
npm run test:coverage
```

**Expected Results:**
- ✅ 0 lint errors
- ✅ 0 TypeScript errors
- ✅ Build < 3 seconds
- ✅ 49+ tests passing
- ✅ Coverage ≥ 75%

#### Step 2: Create Completion Report
```bash
# File: PHASE_5.7_COMPLETION_REPORT.md
# Include:
# - All deliverables ✅
# - Metrics summary
# - Success criteria met ✅
# - Sign-off
```

#### Step 3: Merge to Develop
```bash
git checkout develop
git pull origin develop
git merge phase/5-hardening
git push origin develop
```

#### Step 4: Create Release Tag
```bash
git tag -a v0.5.7 -m "Phase 5.7: Performance & Accessibility"
git push origin v0.5.7
```

#### Step 5: Commit & Finalize
```bash
git add .
git commit -m "[phase-5.7] task-5.7.6: Phase complete, validated, merged"
```

---

## PROGRESS TRACKING

### Current State (progress.json)
```json
{
  "current_phase": "5.7",
  "current_task": "5.7.1",
  "status": "in-progress",
  "tasks_completed": [],
  "phase_start_date": "2026-03-25"
}
```

### After Each Task Completion
Ralph Loop automatically updates:
- `tasks_completed`: adds task ID
- `current_task`: moves to next task
- Commits result to git

### View Real-Time Progress
```bash
# Check what's complete:
cat progress.json | jq '.tasks_completed'

# View last commits:
git log --oneline -10

# Check current status:
cat progress.json | jq '.status'
```

---

## TROUBLESHOOTING

### "No tests found" error
**Cause:** Test files not in correct directory  
**Fix:**
```bash
ls tests/
# Should show: e2e/, visual-regression.spec.ts, fixtures.ts, mocks/
```

### Playwright browsers not installed
**Cause:** Browser binaries missing  
**Fix:**
```bash
npx playwright install --with-deps
```

### Tests timeout / dev server not running
**Cause:** Frontend server not ready  
**Fix:**
```bash
# Terminal 1:
npm run dev  # Wait for "ready on http://localhost:3000"

# Terminal 2:
npx playwright test
```

### Snapshot diff detected (test fails)
**Cause:** Expected (visual change detected)  
**Options:**
1. Review diff: `npx playwright show-report`
2. Accept changes (if intentional): `npx playwright test --update-snapshots`
3. Reject (revert code changes if unintended)

### Git commit fails
**Cause:** Staged files not ready  
**Fix:**
```bash
git status  # See what's unstaged
git add .  # Stage everything
git commit -m "[phase-5.7] task-X: description"
```

---

## COMMAND REFERENCE

### Quick Commands
```bash
# Build frontend
npm run build

# Run E2E tests
npm run test:e2e

# Run coverage check
npm run test:coverage

# Run linting
npm run lint

# Type check
npx tsc --noEmit

# Run specific test
npm run test:e2e -- --grep "Home Page"

# Update snapshots
npx playwright test --update-snapshots

# Show HTML report
npx playwright show-report

# Run Ralph Loop
& ".\ralph-loop.ps1" -Phase "5.7"

# Check git status
git status

# View recent commits
git log --oneline -5

# View progress
cat progress.json | jq '.'
```

---

## ESTIMATED TIMELINE

| Task | Time | Status |
|------|------|--------|
| 5.7.1 | 4 hrs | ⏳ In Progress |
| 5.7.2 | 5 hrs | 📋 Ready |
| 5.7.3 | 6 hrs | 📋 Ready |
| 5.7.4 | 4 hrs | 📋 Ready |
| 5.7.5 | 6 hrs | 📋 Ready |
| 5.7.6 | 3 hrs | 📋 Ready |
| **Total** | **28 hrs** | **27-37 hrs in 1-2 weeks** |

---

## KEY FILES REFERENCE

| File | Purpose | Location |
|------|---------|----------|
| `ralph-loop.ps1` | Automation engine | Project root |
| `progress.json` | State tracking | Project root |
| `RALPH_LOOP_PHASE_5.7_CHECKLIST.md` | Detailed tasks | Project root |
| `PHASE_5.7_EXECUTION_PLAN.md` | Strategic plan | Project root |
| Visual tests | Regression baselines | `frontend/tests/visual-regression.spec.ts` |
| Snapshots | PNG baselines | `frontend/tests/__snapshots__/` |
| Lighthouse reports | Audit results | `reports/lighthouse-*.html` |
| A11y report | Compliance | `reports/WCAG_2.1_AA_AUDIT.md` |

---

## SUCCESS CRITERIA CHECKLIST

### Phase 5.7 Gate (Final)
- [ ] Lighthouse Performance: ≥85
- [ ] Lighthouse Accessibility: ≥90
- [ ] Lighthouse Best Practices: ≥90
- [ ] Lighthouse SEO: ≥90
- [ ] WCAG Critical Violations: 0
- [ ] Code Coverage: ≥75%
- [ ] All Tests Passing: 49+
- [ ] Visual Baselines: 30 captured
- [ ] Build Time: <3s
- [ ] TypeScript Errors: 0

---

## NEXT STEPS

1. **Now:**
   ```powershell
   & ".\ralph-loop.ps1" -Phase "5.7"
   ```

2. **OR manually:**
   - Run Task 5.7.1 (visual regression)
   - Progress through Tasks 5.7.2-5.7.6 sequentially
   - Refer to detailed `RALPH_LOOP_PHASE_5.7_CHECKLIST.md` for subtask details

3. **After completion:**
   - All tests passing ✅
   - Merged to develop ✅
   - Ready for Phase 5.8 or Phase 6 ✅

---

## SUPPORT & ESCALATION

**If Ralph Loop encounters errors:**
1. Check log file: `ralph-loop-[timestamp].log`
2. Review CONTEXT.md for known issues
3. Escalate to human review with `--DryRun` flag

**If test failures occur:**
1. Check test-results/ for failure details
2. Review diffs in HTML report
3. Consult E2E_TEST_GUIDE.md or test comments

---

**Ralph Loop Status:** ✅ READY TO EXECUTE  
**Phase 5.7 Readiness:** ✅ ALL GATES CLEAR  

**Launch Command:**
```powershell
cd "C:\Users\KIIT0001\Downloads\Telegram Desktop\ScentScapeAI\ScentScape"
& ".\ralph-loop.ps1" -Phase "5.7" -MaxIterations 50
```

🚀 **Begin execution immediately**