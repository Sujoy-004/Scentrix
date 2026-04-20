# E2E Test Suite Guide — Scentrix Frontend

## Overview

Comprehensive Playwright E2E test suite covering all critical user journeys: authentication, protected routes, navigation, responsive design, and error handling.

**Test Framework:** Playwright 1.48+  
**Test Runner:** `npx playwright test`  
**Base URL:** `http://localhost:3000`  
**Fixture System:** Custom `fixtures.ts` with `authenticatedPage` fixture  

---

## Test Files

### 1. `fixtures.ts` — Shared Test Utilities

**Purpose:** Provides reusable authentication fixture for tests.

**Features:**
- `authenticatedPage` fixture: Pre-configures page with auth token in localStorage
- Simulates logged-in user state
- Auto-cleanup after each test

**Usage:**
```typescript
import { test, expect } from '../fixtures';

test('should show protected content', async ({ authenticatedPage }) => {
  const page = authenticatedPage;
  await page.goto('/profile');
  expect(page.url()).toContain('/profile');
});
```

---

### 2. `e2e/main-flows.spec.ts` — Core Public & Auth Flows

**Test Groups:**

#### **User Registration & Authentication** (5 tests)
- ✅ Register new user and redirect to quiz
- ✅ Show validation errors for weak passwords
- ✅ Navigate from register to login
- ✅ Prevent authenticated users from accessing login
- ✅ Full auth flow with error handling

**Key Tests:**
- Registration form validation (password strength, email format)
- Error message display (weak passwords, form errors)
- Navigation between auth pages
- Auth state persistence

#### **Navigation Flow** (3 tests)
- ✅ Navigate through main pages (unauthenticated)
- ✅ Navigate to fragrances page
- ✅ Navigate to families page

**Coverage:** Public pages accessible without login

#### **Protected Routes** (4 tests)
- ✅ Redirect to login when accessing quiz without auth
- ✅ Allow access to quiz when authenticated
- ✅ Redirect to login when accessing profile without auth
- ✅ Allow access to profile when authenticated
- ✅ Redirect to login when accessing recommendations

**Key Coverage:** Middleware route protection logic

#### **Logout Flow** (3 tests)
- ✅ Logout user and redirect to home
- ✅ Clear localStorage on logout
- ✅ Redirect to login after post-logout protected route access

**Features:** Complete auth state cleanup, cookie removal, redirect verification

#### **Homepage Features** (2 tests)
- ✅ Display homepage with all sections
- ✅ Working navigation links

#### **Responsive Design** (3 tests)
- ✅ Mobile (375px) rendering
- ✅ Tablet (768px) rendering
- ✅ Desktop (1920px) rendering

**Coverage:** Viewport testing across device sizes

#### **Error Handling** (1 test)
- ✅ Handle network errors gracefully (offline mode)

---

### 3. `e2e/authenticated-flows.spec.ts` — Advanced Authenticated Flows

**Test Groups:**

#### **Authenticated Quiz Flow** (3 tests)
- ✅ Access quiz page when authenticated
- ✅ Display quiz content
- ✅ Handle slider interactions

#### **Authenticated Recommendations** (2 tests)
- ✅ Access recommendations when authenticated
- ✅ See recommendations content

#### **Authenticated Profile** (4 tests)
- ✅ Access profile when authenticated
- ✅ Display profile content
- ✅ Show logout button

#### **Authenticated Wishlist** (1 test)
- ✅ Access wishlist when authenticated

#### **Fragrance Browse Flow** (3 tests)
- ✅ View fragrances page (public)
- ✅ View fragrance detail page
- ✅ View families page (public)

#### **State Persistence** (2 tests)
- ✅ Auth token persists in localStorage
- ✅ Auth state maintained across navigation

#### **Error Recovery** (1 test)
- ✅ Handle missing fragrance gracefully

---

## Running Tests

### Run All Tests
```bash
npm run test:e2e
```

### Run Tests in Specific File
```bash
npx playwright test tests/e2e/main-flows.spec.ts
```

### Run Tests Matching Pattern
```bash
npx playwright test -g "logout"  # Runs all tests with "logout" in name
```

### Run in UI Mode (Interactive)
```bash
npx playwright test --ui
```

### Run in Debug Mode
```bash
npx playwright test --debug
```

### Run Specific Test Only
```bash
npx playwright test tests/e2e/main-flows.spec.ts:20
```

---

## Test Results & Reports

### HTML Report
```bash
npx playwright show-report
```

### View Last Run
```bash
npx playwright show-report ./playwright-report
```

### Screenshot on Failure
Tests automatically capture screenshots on failure (configured in `playwright.config.ts`).

**Location:** `./playwright-report/`

---

## Test Configuration

### Base Configuration (`playwright.config.ts`)
- **Test Directory:** `./tests/e2e`
- **Base URL:** `http://localhost:3000`
- **Timeout:** 30s per test
- **Retries:** 2 on CI, 0 locally
- **Parallelism:** Unlimited locally, 1 on CI
- **WebServer:** Auto-starts `npm run dev` before tests

### Browser Projects
- ✅ Desktop Chrome (Chromium)
- ✅ Desktop Firefox
- ✅ Desktop Safari (WebKit)
- ✅ Mobile Chrome (Pixel 5)
- ✅ Mobile Safari (iPhone 12)

**Skip Mobile:**
```bash
npx playwright test -g "Responsive" --skip-project "Mobile Chrome" --skip-project "Mobile Safari"
```

---

## Fixture Usage Examples

### Using AuthenticatedPage Fixture
```typescript
test('protected action', async ({ authenticatedPage }) => {
  const page = authenticatedPage;
  // page already has auth token set
  // localStorage contains: auth_token, user_id
  // Cookie 'auth_token' is set
  
  await page.goto('/profile');
  expect(page.url()).toContain('/profile');
});
```

### Regular Page Fixture
```typescript
test('public flow', async ({ page }) => {
  // page is unauthenticated
  // No auth token in localStorage
  
  await page.goto('/fragrances');
  expect(page.url()).toContain('/fragrances');
});
```

---

## Test Maintenance

### Adding New Test
1. Add to appropriate file (main-flows.spec.ts or authenticated-flows.spec.ts)
2. Use pattern from existing tests
3. Use `authenticatedPage` fixture for protected routes
4. Use regular `page` fixture for public pages

### Example Template
```typescript
test('should do something', async ({ authenticatedPage }) => {
  const page = authenticatedPage;
  
  // Setup
  await page.goto('/some-page');
  
  // Action
  await page.click('button:has-text("Click me")');
  
  // Assertion
  expect(page.url()).toContain('/expected-path');
});
```

### Common Assertions
```typescript
expect(page.url()).toContain('/fragrances');
expect(page.url()).toBe('http://localhost:3000/');
expect(await page.isVisible('h1')).toBeTruthy();
expect(await page.locator('button').count()).toBeGreaterThan(0);
expect(await page.textContent('body')).toBeTruthy();
```

---

## Troubleshooting

### Tests Timeout
- Check if dev server is running: `npm run dev`
- Increase timeout: `test.setTimeout(60000)`
- Use `--debug` flag to step through

### Auth Tests Failing
- Verify middleware is working
- Check localStorage keys in fixtures
- Ensure auth token format is correct

### Flaky Tests
- Add more `waitForTimeout` or `waitForURL` calls
- Use `waitForSelector` for lazy-loaded content
- Check for race conditions in Zustand store

### Browser Differences
- Use `test.skip()` for unsupported features
- Test in specific browser: `npx playwright test --project chromium`

---

## CI/CD Integration

Tests run automatically on:
- Pull requests (all browsers)
- Commits to main
- Manual trigger via GitHub Actions

**CI Config:** `.github/workflows/playwright.yml`

---

## Coverage Summary

**Total Tests:** 33  
**Coverage Areas:**
- ✅ Authentication (8 tests)
- ✅ Protected Routes (5 tests)
- ✅ Logout Flow (3 tests)
- ✅ Public Navigation (4 tests)
- ✅ Responsive Design (3 tests)
- ✅ Authenticated Features (6 tests)
- ✅ State Management (2 tests)
- ✅ Error Handling (2 tests)

**Critical Paths Covered:**
- ✅ User registration → quiz → recommendations
- ✅ Logout → redirect → protected route access
- ✅ Protected route access control
- ✅ Mobile/tablet/desktop rendering
- ✅ Auth state persistence across navigation

---

## Last Updated
January 2025  
**Test Suite Version:** 2.0 (Fixtures + comprehensive coverage)
