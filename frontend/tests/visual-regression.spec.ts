import { test, expect } from '@playwright/test';

/**
 * PHASE 5.7 TASK 5.7.1: Visual Regression Testing
 * 
 * This test suite captures visual baselines for all 11 pages across 3 breakpoints:
 * - Desktop (1280px)
 * - Tablet (768px)
 * - Mobile (375px)
 * 
 * Total Snapshots: 30 baselines (11 pages × 3 breakpoints)
 * 
 * To update baselines (after visual intentional changes):
 *   npx playwright test tests/visual-regression.spec.ts --update-snapshots
 * 
 * To review snapshots:
 *   npx playwright test tests/visual-regression.spec.ts --headed
 */

// Define viewport sizes for different breakpoints
const BREAKPOINTS = {
  desktop: { width: 1280, height: 720 },
  tablet: { width: 768, height: 1024 },
  mobile: { width: 375, height: 812 },
};

// Helper function to set viewport and capture snapshot
async function captureSnapshot(
  page: any,
  breakpoint: 'desktop' | 'tablet' | 'mobile',
  snapshotName: string
) {
  await page.setViewportSize(BREAKPOINTS[breakpoint]);
  // Wait for any animations/transitions to complete
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);
  
  // Capture snapshot
  const fullSnapshotName = `${snapshotName}-${breakpoint}.png`;
  await expect(page).toHaveScreenshot(fullSnapshotName, {
    maxDiffPixels: 100,
    threshold: 0.2,
  });
}

// ============================================================================
// VISUAL REGRESSION TESTS - ALL 11 PAGES × 3 BREAKPOINTS = 30 SNAPSHOTS
// ============================================================================

test.describe('Visual Regression Tests - Page Baselines', () => {
  
  test.describe('1. Home Page (/) - 3 Breakpoints', () => {
    
    test('1a. Home Page - Desktop (1280px)', async ({ page }) => {
      await page.goto('/');
      await captureSnapshot(page, 'desktop', 'home');
    });
    
    test('1b. Home Page - Tablet (768px)', async ({ page }) => {
      await page.goto('/');
      await captureSnapshot(page, 'tablet', 'home');
    });
    
    test('1c. Home Page - Mobile (375px)', async ({ page }) => {
      await page.goto('/');
      await captureSnapshot(page, 'mobile', 'home');
    });
  });

  test.describe('2. Fragrances List Page (/fragrances) - 3 Breakpoints', () => {
    
    test('2a. Fragrances List - Desktop (1280px)', async ({ page }) => {
      await page.goto('/fragrances');
      await captureSnapshot(page, 'desktop', 'fragrances-list');
    });
    
    test('2b. Fragrances List - Tablet (768px)', async ({ page }) => {
      await page.goto('/fragrances');
      await captureSnapshot(page, 'tablet', 'fragrances-list');
    });
    
    test('2c. Fragrances List - Mobile (375px)', async ({ page }) => {
      await page.goto('/fragrances');
      await captureSnapshot(page, 'mobile', 'fragrances-list');
    });
  });

  test.describe('3. Fragrance Detail Page (/fragrances/:id) - 3 Breakpoints', () => {
    
    test('3a. Fragrance Detail - Desktop (1280px)', async ({ page }) => {
      // Use mock fragrance ID or first available
      await page.goto('/fragrances/1');
      await captureSnapshot(page, 'desktop', 'fragrance-detail');
    });
    
    test('3b. Fragrance Detail - Tablet (768px)', async ({ page }) => {
      await page.goto('/fragrances/1');
      await captureSnapshot(page, 'tablet', 'fragrance-detail');
    });
    
    test('3c. Fragrance Detail - Mobile (375px)', async ({ page }) => {
      await page.goto('/fragrances/1');
      await captureSnapshot(page, 'mobile', 'fragrance-detail');
    });
  });

  test.describe('4. Fragrance Families Page (/families) - 3 Breakpoints', () => {
    
    test('4a. Families Page - Desktop (1280px)', async ({ page }) => {
      await page.goto('/families');
      await captureSnapshot(page, 'desktop', 'families');
    });
    
    test('4b. Families Page - Tablet (768px)', async ({ page }) => {
      await page.goto('/families');
      await captureSnapshot(page, 'tablet', 'families');
    });
    
    test('4c. Families Page - Mobile (375px)', async ({ page }) => {
      await page.goto('/families');
      await captureSnapshot(page, 'mobile', 'families');
    });
  });

  test.describe('5. Onboarding Quiz Page (/onboarding/quiz) - 3 Breakpoints', () => {
    
    test('5a. Quiz Page - Desktop (1280px)', async ({ page }) => {
      await page.goto('/onboarding/quiz');
      await captureSnapshot(page, 'desktop', 'quiz');
    });
    
    test('5b. Quiz Page - Tablet (768px)', async ({ page }) => {
      await page.goto('/onboarding/quiz');
      await captureSnapshot(page, 'tablet', 'quiz');
    });
    
    test('5c. Quiz Page - Mobile (375px)', async ({ page }) => {
      await page.goto('/onboarding/quiz');
      await captureSnapshot(page, 'mobile', 'quiz');
    });
  });

  test.describe('6. Recommendations Page (/recommendations) - 3 Breakpoints', () => {
    
    test('6a. Recommendations - Desktop (1280px)', async ({ page }) => {
      // Note: May require mocked data or auth flow
      await page.goto('/recommendations');
      await captureSnapshot(page, 'desktop', 'recommendations');
    });
    
    test('6b. Recommendations - Tablet (768px)', async ({ page }) => {
      await page.goto('/recommendations');
      await captureSnapshot(page, 'tablet', 'recommendations');
    });
    
    test('6c. Recommendations - Mobile (375px)', async ({ page }) => {
      await page.goto('/recommendations');
      await captureSnapshot(page, 'mobile', 'recommendations');
    });
  });

  test.describe('7. Login Page (/auth/login) - 3 Breakpoints', () => {
    
    test('7a. Login Page - Desktop (1280px)', async ({ page }) => {
      await page.goto('/auth/login');
      await captureSnapshot(page, 'desktop', 'login');
    });
    
    test('7b. Login Page - Tablet (768px)', async ({ page }) => {
      await page.goto('/auth/login');
      await captureSnapshot(page, 'tablet', 'login');
    });
    
    test('7c. Login Page - Mobile (375px)', async ({ page }) => {
      await page.goto('/auth/login');
      await captureSnapshot(page, 'mobile', 'login');
    });
  });

  test.describe('8. Register Page (/auth/register) - 3 Breakpoints', () => {
    
    test('8a. Register Page - Desktop (1280px)', async ({ page }) => {
      await page.goto('/auth/register');
      await captureSnapshot(page, 'desktop', 'register');
    });
    
    test('8b. Register Page - Tablet (768px)', async ({ page }) => {
      await page.goto('/auth/register');
      await captureSnapshot(page, 'tablet', 'register');
    });
    
    test('8c. Register Page - Mobile (375px)', async ({ page }) => {
      await page.goto('/auth/register');
      await captureSnapshot(page, 'mobile', 'register');
    });
  });

  test.describe('9. User Profile Page (/profile) - 3 Breakpoints', () => {
    
    test('9a. Profile Page - Desktop (1280px)', async ({ page }) => {
      // Requires authentication (can be mocked via MSW)
      await page.goto('/profile');
      await captureSnapshot(page, 'desktop', 'profile');
    });
    
    test('9b. Profile Page - Tablet (768px)', async ({ page }) => {
      await page.goto('/profile');
      await captureSnapshot(page, 'tablet', 'profile');
    });
    
    test('9c. Profile Page - Mobile (375px)', async ({ page }) => {
      await page.goto('/profile');
      await captureSnapshot(page, 'mobile', 'profile');
    });
  });

  test.describe('10. Wishlist Page (/profile/wishlist) - 3 Breakpoints', () => {
    
    test('10a. Wishlist Page - Desktop (1280px)', async ({ page }) => {
      await page.goto('/profile/wishlist');
      await captureSnapshot(page, 'desktop', 'wishlist');
    });
    
    test('10b. Wishlist Page - Tablet (768px)', async ({ page }) => {
      await page.goto('/profile/wishlist');
      await captureSnapshot(page, 'tablet', 'wishlist');
    });
    
    test('10c. Wishlist Page - Mobile (375px)', async ({ page }) => {
      await page.goto('/profile/wishlist');
      await captureSnapshot(page, 'mobile', 'wishlist');
    });
  });

  test.describe('11. Search Results Page (/search) - 3 Breakpoints', () => {
    
    test('11a. Search Results - Desktop (1280px)', async ({ page }) => {
      await page.goto('/search?q=rose');
      await captureSnapshot(page, 'desktop', 'search');
    });
    
    test('11b. Search Results - Tablet (768px)', async ({ page }) => {
      await page.goto('/search?q=rose');
      await captureSnapshot(page, 'tablet', 'search');
    });
    
    test('11c. Search Results - Mobile (375px)', async ({ page }) => {
      await page.goto('/search?q=rose');
      await captureSnapshot(page, 'mobile', 'search');
    });
  });
});

// ============================================================================
// SCREENSHOT BASELINE UPDATE INSTRUCTIONS
// ============================================================================
/**
 * INSTRUCTIONS FOR MAINTAINING BASELINES:
 * 
 * 1. INITIAL CAPTURE (what you're doing now):
 *    npx playwright test tests/visual-regression.spec.ts --update-snapshots
 *    This creates all 30 baseline snapshots in tests/__snapshots__/
 * 
 * 2. REVIEWING EXISTING BASELINES:
 *    npx playwright test tests/visual-regression.spec.ts --headed
 *    Opens browser window so you can visually inspect each page
 * 
 * 3. AFTER INTENTIONAL VISUAL CHANGES:
 *    If you intentionally change styling (e.g., color scheme, layout):
 *    npx playwright test tests/visual-regression.spec.ts --update-snapshots
 *    This updates baselines to new design
 * 
 * 4. REGRESSION DETECTION:
 *    npx playwright test tests/visual-regression.spec.ts
 *    If visual changes are unintended, test will FAIL with diff images
 *    Located in: test-results/[test-name]-diff.png
 * 
 * 5. INTERPRETING FAILURES:
 *    - Minor pixel differences (< 100px) are typically acceptable
 *    - Threshold set to 0.2 (20% diff) to allow for slight render variations
 *    - Adjust maxDiffPixels or threshold if flaky on specific pages
 */
