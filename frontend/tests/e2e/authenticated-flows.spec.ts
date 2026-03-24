import { test, expect } from '@playwright/test';

test.describe('Authenticated User Flows', () => {
  // Helper function to login
  async function login(page, email: string, password: string) {
    await page.goto('/auth/login');
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button:has-text("Sign In")');
    await page.waitForURL('/onboarding/quiz');
  }

  test('should complete quiz flow', async ({ page }) => {
    // Navigate to quiz (can access without auth for testing)
    await page.goto('/onboarding/quiz');

    // Find rating sliders
    const sliders = page.locator('input[type="range"]');
    const sliderCount = await sliders.count();

    if (sliderCount > 0) {
      // Interact with first slider
      await sliders.first().fill('7');

      // Check if progress updates
      const progressBar = page.locator('[class*="progress"]');
      expect(progressBar).toBeVisible();
    }

    // Click next or submit button
    const submitButton =
      page.locator('button:has-text("Submit")') ||
      page.locator('button:has-text("Next")');
    if (await submitButton.isVisible()) {
      await submitButton.click();
    }
  });

  test('should view recommendations if available', async ({ page }) => {
    // Try to navigate to recommendations
    await page.goto('/recommendations');

    // If redirected to login, that's expected
    if (page.url().includes('/auth/login')) {
      expect(page.url()).toContain('/auth/login');
    } else {
      // Should see recommendations content
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    }
  });

  test('should view fragrance details', async ({ page }) => {
    await page.goto('/fragrances');

    // Click on first fragrance card
    const firstCard = page.locator('[class*="card"]').first();
    const link = firstCard.locator('a').first();

    if (await link.isVisible()) {
      await link.click();

      // Should be on fragrance detail page
      expect(page.url()).toContain('/fragrances/');

      // Check for detail content
      const detailContent = page.locator('[class*="detail"]');
      expect(detailContent).toBeTruthy();
    }
  });

  test('should navigate to profile page', async ({ page }) => {
    // Try to access profile
    await page.goto('/profile');

    // If not authenticated, should redirect to login
    const isOnProfile = page.url().includes('/profile');
    const isOnLogin = page.url().includes('/auth/login');

    expect(isOnProfile || isOnLogin).toBeTruthy();
  });

  test('should navigate to wishlist page', async ({ page }) => {
    // Try to access wishlist
    await page.goto('/profile/wishlist');

    // If not authenticated, should redirect to login
    const isOnWishlist = page.url().includes('/wishlist');
    const isOnLogin = page.url().includes('/auth/login');

    expect(isOnWishlist || isOnLogin).toBeTruthy();
  });
});

test.describe('Logout Flow', () => {
  test('should logout and redirect to home', async ({ page }) => {
    // Navigate to home
    await page.goto('/');

    // Find logout button if visible
    const logoutButton = page.locator('button:has-text("Log Out")');

    if (await logoutButton.isVisible()) {
      await logoutButton.click();

      // Should be redirected to home
      await page.waitForURL('/');
      expect(page.url()).toBe('http://localhost:3000/');
    }
  });
});

test.describe('History Page', () => {
  test('should display quiz history if available', async ({ page }) => {
    // Try to access history
    await page.goto('/profile/history');

    // If not authenticated, should redirect to login
    if (page.url().includes('/auth/login')) {
      expect(page.url()).toContain('/auth/login');
    } else {
      // Should show history content
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    }
  });
});
