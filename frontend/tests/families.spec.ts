import { test, expect } from '@playwright/test';

test.describe('families pages', () => {
  test('landing shows 10 families, cards drill into detail pages', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    const cards = page.locator('.elite-family-card');
    await cards.first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(800);
    const count = await cards.count();
    console.log('landing family cards:', count);
    expect(count).toBe(10);

    await cards.first().click();
    await page.waitForURL(/\/families\/[a-z]+/, { timeout: 15000 });
    console.log('landing card drill URL:', page.url());
    expect(page.url()).toMatch(/\/families\/[a-z]+/);
  });

  test('/families shows all 18 families with clickable cards', async ({ page }) => {
    await page.goto('/families', { waitUntil: 'domcontentloaded' });
    const cards = page.locator('.elite-family-card');
    await cards.first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(800);
    const count = await cards.count();
    console.log('/families card count:', count);
    expect(count).toBe(18);

    await cards.first().click();
    await page.waitForURL(/\/families\/[a-z]+/, { timeout: 15000 });
    console.log('/families card drill URL:', page.url());
    expect(page.url()).toMatch(/\/families\/[a-z]+/);
  });

  test('family detail page loads fragrance cards from the API', async ({ page }) => {
    await page.goto('/families/woody', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);
    const url = page.url();
    console.log('woody detail URL:', url);
    expect(url).toContain('/families/woody');

    const title = page.locator('.family-title');
    if (await title.count()) {
      const t = await title.innerText();
      console.log('detail title:', t);
      expect(t).toContain('Woody');
    }

    const cards = page.locator('.fragrance-card-elite');
    const n = await cards.count();
    console.log('woody fragrance cards:', n);
    expect(n).toBeGreaterThan(0);
  });

  test('unknown family slug shows not-found state', async ({ page }) => {
    await page.goto('/families/not-a-family', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    const text = await page.locator('body').innerText();
    console.log('unknown family body has not-found:', text.includes('Family not found'));
    expect(text).toContain('Family not found');
  });
});