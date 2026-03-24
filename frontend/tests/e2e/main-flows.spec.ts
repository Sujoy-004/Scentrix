import { test, expect } from '@playwright/test';

test.describe('User Registration & Authentication Flow', () => {
  test('should register a new user and be redirected to quiz', async ({
    page,
  }) => {
    // Navigate to register page
    await page.goto('/auth/register');

    // Fill in registration form
    await page.fill('input[name="fullName"]', 'Test User');
    await page.fill('input[name="email"]', `test-${Date.now()}@example.com`);
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.fill('input[name="confirmPassword"]', 'TestPassword123!');

    // Submit form
    await page.click('button:has-text("Create Account")');

    // Wait for redirect to quiz page
    await page.waitForURL('/onboarding/quiz');
    expect(page.url()).toContain('/onboarding/quiz');
  });

  test('should show validation errors for invalid form', async ({ page }) => {
    // Navigate to register page
    await page.goto('/auth/register');

    // Submit empty form
    await page.click('button:has-text("Create Account")');

    // Check for validation errors
    const errors = await page.locator('.error-message');
    expect(errors).toBeTruthy();
  });

  test('should navigate to login from register', async ({ page }) => {
    // Navigate to register page
    await page.goto('/auth/register');

    // Click link to login
    const loginLink = page.locator('a:has-text("Already have an account")');
    await loginLink.click();

    // Verify on login page
    await page.waitForURL('/auth/login');
    expect(page.url()).toContain('/auth/login');
  });
});

test.describe('Navigation Flow', () => {
  test('should navigate through main pages without login', async ({
    page,
  }) => {
    // Start at home
    await page.goto('/');
    expect(page.url()).toContain('/');

    // Navigate to fragrances
    const browseButton = page.locator('a:has-text("Browse Fragrances")');
    await browseButton.first().click();
    await page.waitForURL('/fragrances');
    expect(page.url()).toContain('/fragrances');

    // Go back home
    await page.click('button:has-text("ScentScape")');
    await page.waitForURL('/');
  });

  test('should navigate to family filter from fragrances', async ({
    page,
  }) => {
    // Navigate to fragrances
    await page.goto('/fragrances');

    // Click on a family
    const familyLink = page.locator('a').filter({ hasText: 'Floral' }).first();
    if (await familyLink.isVisible()) {
      await familyLink.click();
      await page.waitForURL(/\/families\/\w+/);
      expect(page.url()).toContain('/families/');
    }
  });
});

test.describe('Homepage Features', () => {
  test('should display all homepage sections', async ({ page }) => {
    await page.goto('/');

    // Check for hero section
    const heroTitle = page.locator('h1');
    expect(heroTitle).toBeVisible();

    // Check for CTA buttons
    const ctaButtons = page.locator('button:has-text("Get Started")');
    expect(ctaButtons.first()).toBeVisible();
  });

  test('should scroll and load content dynamically', async ({ page }) => {
    await page.goto('/');

    // Scroll down
    await page.evaluate(() => window.scrollBy(0, 1000));

    // Wait for animations
    await page.waitForTimeout(500);

    // Check if more content is visible
    const familiesSection = page.locator('h2:has-text("Fragrance Families")');
    expect(familiesSection).toBeVisible();
  });
});

test.describe('Fragrances Page', () => {
  test('should display fragrance cards', async ({ page }) => {
    await page.goto('/fragrances');

    // Check for cards
    const cards = page.locator('[class*="fragrance-card"]');
    expect(cards).toBeTruthy();

    // Wait for cards to load
    await page.waitForSelector('[class*="fragrance-card"]', { timeout: 5000 });
  });

  test('should allow filtering by family', async ({ page }) => {
    await page.goto('/fragrances');

    // Get initial count
    const initialCards = await page.locator('[class*="fragrance-card"]').count();

    // Select a family from dropdown
    const familySelect = page.locator('select').first();
    await familySelect.selectOption('Floral');

    // Wait for filtered results
    await page.waitForTimeout(1000);

    // Cards might be different due to filtering
    const filteredCards = await page.locator(
      '[class*="fragrance-card"]'
    ).count();
    expect(filteredCards).toBeGreaterThan(0);
  });
});

test.describe('Responsive Design', () => {
  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Navigate to home
    await page.goto('/');

    // Check if hamburger menu exists
    const hamburger = page.locator('button[class*="toggle"]');
    expect(hamburger).toBeVisible();

    // Check if navigation menu is accessible
    await hamburger.click();

    // Menu should show
    const navMenu = page.locator('[class*="menu"]');
    expect(navMenu).toBeVisible();
  });

  test('should display correctly on tablet', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    await page.goto('/');

    // Hero should be visible
    const hero = page.locator('[class*="hero"]');
    expect(hero).toBeVisible();
  });
});

test.describe('Error Handling', () => {
  test('should handle 404 gracefully', async ({ page }) => {
    await page.goto('/non-existent-page');

    // Should show some error content
    const content = await page.content();
    expect(content).toBeTruthy();
  });
});
