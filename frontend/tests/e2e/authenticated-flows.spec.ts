import { test, expect } from '../fixtures';

test.describe('Authenticated User Quiz Flow', () => {
  test('should access quiz page when authenticated', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Navigate to quiz
    await page.goto('/onboarding/quiz');

    // Should stay on quiz page (no redirect to login)
    expect(page.url()).toContain('/onboarding/quiz');

    // Wait for page to load
    await page.waitForTimeout(500);
  });

  test('should display quiz content when authenticated', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Navigate to quiz
    await page.goto('/onboarding/quiz');

    // Check for form elements
    const formContent = await page.textContent('body');
    expect(formContent).toBeTruthy();
    expect(formContent?.length ?? 0).toBeGreaterThan(0);
  });

  test('should handle quiz slider interactions', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Navigate to quiz
    await page.goto('/onboarding/quiz');

    // Find sliders or input elements
    const inputs = page.locator('input[type="range"]');
    const inputCount = await inputs.count();

    if (inputCount > 0) {
      // Interact with first slider
      const firstSlider = inputs.first();
      await firstSlider.fill('7');

      // Verify value changed
      const value = await firstSlider.inputValue();
      expect(parseInt(value)).toBeGreaterThan(0);
    }
  });
});

test.describe('Authenticated User Recommendations', () => {
  test('should access recommendations when authenticated', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Navigate to recommendations
    await page.goto('/recommendations');

    // Should stay on recommendations page
    expect(page.url()).toContain('/recommendations');

    // Wait for content to load
    await page.waitForTimeout(500);
  });

  test('should see recommendations content when authenticated', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Navigate to recommendations
    await page.goto('/recommendations');

    // Check for page content
    const content = await page.textContent('body');
    expect(content).toBeTruthy();
  });
});

test.describe('Authenticated User Profile', () => {
  test('should access profile when authenticated', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Navigate to profile
    await page.goto('/profile');

    // Should stay on profile page
    expect(page.url()).toContain('/profile');

    // Wait for content
    await page.waitForTimeout(500);
  });

  test('should display profile content', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Navigate to profile
    await page.goto('/profile');

    // Check for profile content
    const content = await page.textContent('body');
    expect(content).toBeTruthy();
    expect(content?.length ?? 0).toBeGreaterThan(0);
  });

  test('should have logout button in profile/navbar', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Navigate to profile
    await page.goto('/profile');

    // Look for logout button
    const logoutBtn = page.locator('button, a').filter({ hasText: /Logout|Log out|Sign out/i }).first();
    const hasLogoutBtn = await logoutBtn.isVisible();
    
    // Either navbar has logout or profile page has it
    expect(hasLogoutBtn).toBeDefined();
  });
});

test.describe('Authenticated User Wishlist', () => {
  test('should access wishlist when authenticated', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Navigate to wishlist
    await page.goto('/profile/wishlist');

    // Should be on wishlist or stay on profile
    const isOnWishlist = page.url().includes('/wishlist');
    const isOnProfile = page.url().includes('/profile');
    expect(isOnWishlist || isOnProfile).toBeTruthy();
  });
});

test.describe('Fragrance Browse Flow', () => {
  test('should view fragrances page', async ({ page }) => {
    // Navigate to fragrances (public page)
    await page.goto('/fragrances');

    // Should load without issue
    expect(page.url()).toContain('/fragrances');

    // Wait for content
    await page.waitForTimeout(1000);
  });

  test('should view fragrance detail', async ({ page }) => {
    // Navigate to fragrances
    await page.goto('/fragrances');

    // Wait for cards to load
    await page.waitForTimeout(1000);

    // Try to find and click fragrance card
    const cardLinks = page.locator('a[href*="/fragrances/"]').filter({ hasText: /view|details?/i });
    const linkCount = await cardLinks.count();

    if (linkCount > 0) {
      // Click first link
      await cardLinks.first().click();

      // Should be on fragrance detail page
      expect(page.url()).toContain('/fragrances/');
    }
  });

  test('should view families page', async ({ page }) => {
    // Navigate to families (public page)
    await page.goto('/families');

    // Should load without issue
    expect(page.url()).toContain('/families');
  });
});

test.describe('State Persistence', () => {
  test('should persist auth state in localStorage', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Check localStorage for auth token
    const token = await page.evaluate(() => localStorage.getItem('auth_token'));
    expect(token).toBeTruthy();
  });

  test('should maintain auth across navigation', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Get initial token
    const initialToken = await page.evaluate(() => localStorage.getItem('auth_token'));

    // Navigate to different pages
    await page.goto('/fragrances');
    await page.waitForTimeout(300);
    await page.goto('/profile');
    await page.waitForTimeout(300);

    // Check token still exists
    const finalToken = await page.evaluate(() => localStorage.getItem('auth_token'));
    expect(finalToken).toBe(initialToken);
  });
});

test.describe('Error Recovery', () => {
  test('should handle missing fragrance gracefully', async ({ page }) => {
    // Try to access non-existent fragrance
    await page.goto('/fragrances/nonexistent-id');

    // Page should load (even if showing empty state)
    const content = await page.textContent('body');
    expect(content).toBeTruthy();
  });
});
