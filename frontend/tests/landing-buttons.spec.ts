import { test, expect } from '@playwright/test';

test.describe('landing page buttons', () => {
  test('all navbar + hero + families + CTA buttons navigate', async ({ page }) => {
    const cases: { name: string; btn: string; path: string }[] = [
      { name: 'navbar Discover', btn: 'Discover', path: '/recommendations' },
      { name: 'navbar Quiz', btn: 'Quiz', path: '/quiz' },
      { name: 'navbar Families', btn: 'Families', path: '/families' },
      { name: 'navbar Log In', btn: 'Log In', path: '/auth/login' },
      { name: 'hero Start Discovery', btn: 'Start Discovery', path: '/quiz' },
      { name: 'hero Browse Library', btn: 'Browse Library', path: '/families' },
      { name: 'hero Browse Popular Picks', btn: 'Browse Popular Picks', path: '/recommendations' },
      { name: 'families Explore More', btn: 'Explore More', path: '/families' },
      { name: 'final CTA Start Your Protocol', btn: 'Start Your Protocol', path: '/quiz' },
    ];

    for (const c of cases) {
      await page.goto('/', { waitUntil: 'domcontentloaded' });
      const btn = page.getByRole('button', { name: new RegExp(c.btn, 'i') }).first();
      await btn.scrollIntoViewIfNeeded();
      await page.waitForTimeout(400);
      await btn.click();
      await page.waitForURL(new RegExp(c.path), { timeout: 15000 });
      console.log(`PASS ${c.name}: ${page.url()}`);
    }
  });

  test('cookie banner appears only after scrolling, never blocks first-load CTAs', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    expect(await page.locator('#cookie-consent-banner').count()).toBe(0);

    await page.evaluate(() => window.scrollTo(0, 400));
    await page.waitForTimeout(500);
    expect(await page.locator('#cookie-consent-banner').count()).toBe(1);
  });

  test('family cards navigate to families page', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    const card = page.locator('.elite-family-card').first();
    await card.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    await card.click();
    await page.waitForURL(/\/families/, { timeout: 15000 });
    console.log('family card URL:', page.url());
  });
});