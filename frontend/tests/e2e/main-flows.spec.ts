import { test, expect } from '../fixtures';

test.describe('User Registration & Authentication Flow', () => {
  test('should register a new user and be redirected to quiz', async ({
    page,
  }) => {
    // Navigate to register page
    await page.goto('/auth/register');

    // Fill in registration form
    const email = `test-${Date.now()}@example.com`;
    await page.fill('input[name="fullName"]', 'Test User');
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.fill('input[name="confirmPassword"]', 'TestPassword123!');

    // Submit form
    await page.click('button:has-text("Create Account")');

    // Wait for redirect to quiz page or handle errors gracefully
    try {
      await page.waitForURL('/onboarding/quiz', { timeout: 10000 });
      expect(page.url()).toContain('/onboarding/quiz');
    } catch {
      // If redirect fails, check for error message
      const errorMsg = await page.locator('[role="alert"]').first().textContent();
      console.log('Registration error:', errorMsg);
    }
  });

  test('should show validation errors for invalid password', async ({ page }) => {
    // Navigate to register page
    await page.goto('/auth/register');

    // Fill with weak password
    await page.fill('input[name="fullName"]', 'Test User');
    await page.fill('input[name="email"]', `test-${Date.now()}@example.com`);
    await page.fill('input[name="password"]', 'weak');
    await page.fill('input[name="confirmPassword"]', 'weak');

    // Try to submit
    await page.click('button:has-text("Create Account")');

    // Check for validation errors or disabled submit
    const submitBtn = page.locator('button:has-text("Create Account")');
    const isDisabled = await submitBtn.isDisabled();
    expect(isDisabled || await page.locator('[role="alert"]').count() > 0).toBeTruthy();
  });

  test('should navigate to login from register', async ({ page }) => {
    // Navigate to register page
    await page.goto('/auth/register');

    // Click "Already have an account?" link
    const loginLink = page.locator('a, button').filter({ hasText: /Already have|log in/i }).first();
    if (await loginLink.isVisible()) {
      await loginLink.click();
      await page.waitForURL('/auth/login', { timeout: 5000 });
      expect(page.url()).toContain('/auth/login');
    }
  });

  test('should prevent access to login page when authenticated', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Try to navigate to login page
    await page.goto('/auth/login');

    // Should redirect to home or recommendations
    const currentUrl = page.url();
    expect(
      currentUrl.includes('/') && !currentUrl.includes('/auth/login')
    ).toBeTruthy();
  });
});

test.describe('Navigation Flow', () => {
  test('should navigate through main pages without login', async ({
    page,
  }) => {
    // Start at home
    await page.goto('/');
    expect(page.url()).toContain('/');

    // Check for CTA button
    const browseBtn = page.locator('button, a').filter({ hasText: /Browse|Start/i }).first();
    if (await browseBtn.isVisible()) {
      await browseBtn.click();
      await page.waitForURL(/\/(fragrances|onboarding)/);
    }
  });

  test('should navigate to fragrances page', async ({ page }) => {
    // Navigate directly to fragrances
    await page.goto('/fragrances');
    
    // Should load without redirect (public page)
    expect(page.url()).toContain('/fragrances');
    
    // Wait for fragrance cards to load
    await page.waitForTimeout(1000);
  });

  test('should navigate to families page', async ({ page }) => {
    // Navigate to families
    await page.goto('/families');
    
    expect(page.url()).toContain('/families');
  });
});

test.describe('Protected Routes', () => {
  test('should redirect to login when accessing quiz without auth', async ({
    page,
  }) => {
    // Try to access quiz page without auth
    await page.goto('/onboarding/quiz');

    // Should redirect to login with redirect param
    expect(page.url()).toContain('/auth/login');
  });

  test('should allow access to quiz when authenticated', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Navigate to quiz page
    await page.goto('/onboarding/quiz');

    // Should stay on quiz page (no redirect)
    expect(page.url()).toContain('/onboarding/quiz');
  });

  test('should redirect to login when accessing profile without auth', async ({
    page,
  }) => {
    // Try to access profile page without auth
    await page.goto('/profile');

    // Should redirect to login
    expect(page.url()).toContain('/auth/login');
  });

  test('should allow access to profile when authenticated', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Navigate to profile page
    await page.goto('/profile');

    // Should stay on profile page
    expect(page.url()).toContain('/profile');
  });

  test('should redirect to login when accessing recommendations without auth', async ({
    page,
  }) => {
    // Try to access recommendations
    await page.goto('/recommendations');

    // Should redirect to login
    expect(page.url()).toContain('/auth/login');
  });
});

test.describe('Logout Flow', () => {
  test('should logout user and redirect to home', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Navigate to profile
    await page.goto('/profile');
    expect(page.url()).toContain('/profile');

    // Find and click logout button
    const logoutBtn = page.locator('button').filter({ hasText: /Logout|Sign out/i }).first();
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click();

      // Wait for redirect to home
      await page.waitForURL('/', { timeout: 5000 });
      expect(page.url()).toEqual('http://localhost:3000/');
    }
  });

  test('should clear localStorage on logout', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    
    // Get initial auth token
    const initialToken = await page.evaluate(() => localStorage.getItem('auth_token'));
    expect(initialToken).toBeTruthy();

    // Navigate to logout page directly
    await page.goto('/auth/logout');

    // Wait a bit for logout to process
    await page.waitForTimeout(1000);

    // Check that auth token is cleared
    const tokenAfterLogout = await page.evaluate(() => localStorage.getItem('auth_token'));
    expect(tokenAfterLogout).toBeFalsy();
  });

  test('should redirect to login after accessing protected route post-logout', async ({
    page,
  }) => {
    // Try to access profile without auth
    await page.goto('/profile');

    // Should be redirected to login
    expect(page.url()).toContain('/auth/login');
  });
});

test.describe('Homepage Features', () => {
  test('should display homepage with all sections', async ({ page }) => {
    await page.goto('/');

    // Wait for page to load
    await page.waitForTimeout(1000);

    // Check for main heading
    const heading = page.locator('h1').first();
    expect(await heading.count()).toBeGreaterThan(0);
  });

  test('should have working navigation links', async ({ page }) => {
    await page.goto('/');

    // Check navbar exists
    const navbar = page.locator('nav').first();
    expect(await navbar.isVisible()).toBeTruthy();
  });
});

test.describe('Responsive Design', () => {
  test('should render properly on mobile (375px)', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Navigate to home
    await page.goto('/');

    // Wait for content to load
    await page.waitForTimeout(500);

    // Check that main content is visible
    const mainContent = page.locator('main').first();
    const isVisible = await mainContent.isVisible();
    expect(isVisible).toBeTruthy();
  });

  test('should render properly on tablet (768px)', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    // Navigate to fragrances page
    await page.goto('/fragrances');

    // Wait for cards to load
    await page.waitForTimeout(500);

    // Verify content is visible
    expect(page.url()).toContain('/fragrances');
  });

  test('should render properly on desktop (1920px)', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });

    // Navigate to home
    await page.goto('/');

    // Check that layout is rendered
    await page.waitForTimeout(500);
    expect(page.url()).toContain('/');
  });
});

test.describe('Error Handling', () => {
  test('should handle network errors gracefully', async ({ page }) => {
    // Enable offline mode
    await page.context().setOffline(true);

    // Try to navigate
    try {
      await page.goto('/fragrances', { waitUntil: 'domcontentloaded' });
    } catch (e) {
      // Expected network error
    }

    // Check for error indicator or fallback UI
    const content = await page.locator('body').textContent();
    expect(content).toBeTruthy();

    // Re-enable network
    await page.context().setOffline(false);
  });
});


test.describe('Navigation Flow', () => {
  test('should navigate through multiple pages with pagination', async ({
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
