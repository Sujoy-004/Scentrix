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

    const famBadge = page.locator('.fragrance-card-elite .rounded-full span').first();
    if (await famBadge.count()) {
      const fam = await famBadge.innerText();
      console.log('first card family badge:', fam);
      expect(fam.trim().toLowerCase()).toBe('woody');
    }
  });

  test('all family cards share the page primary accord', async ({ page }) => {
    await page.goto('/families/woody', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);
    const badges = page.locator('.fragrance-card-elite .rounded-full span');
    const texts = await badges.allInnerTexts();
    const clean = texts.map((t) => t.trim().toLowerCase()).filter(Boolean);
    console.log('sample family badges:', clean.slice(0, 12));
    expect(clean.length).toBeGreaterThan(0);
    for (const fam of clean) {
      expect(fam).toContain('woody');
    }
  });

  test('5 cards per row on wide viewport (family + recommendations)', async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 900 });
    await page.goto('/families/woody', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);
    const cards = page.locator('.fragrance-card-elite');
    const n = await cards.count();
    expect(n).toBeGreaterThan(0);
    const box0 = (await cards.nth(0).boundingBox())!;
    const box4 = (await cards.nth(4).boundingBox())!;
    const box5 = (await cards.nth(5).boundingBox())!;
    const sameRow = Math.abs(box0.y - box4.y) < 4;
    const nextRow = box5.y > box4.y + 10;
    console.log('card widths:', box0.width, 'row0 y0/y4:', box0.y, box4.y, 'y5:', box5.y);
    expect(sameRow).toBe(true);
    expect(nextRow).toBe(true);
    expect(box0.width).toBeGreaterThan(200);

    await page.goto('/recommendations', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);
    const rc = page.locator('.fragrance-card-elite');
    const rcCount = await rc.count();
    if (rcCount > 0) {
      const rb0 = (await rc.nth(0).boundingBox())!;
      const rb4 = (await rc.nth(4).boundingBox())!;
      console.log('recommendations widths:', rb0.width, 'y0/y4:', rb0.y, rb4.y);
      expect(Math.abs(rb0.y - rb4.y)).toBeLessThan(4);
    }
  });

  test('unknown family slug shows not-found state', async ({ page }) => {
    await page.goto('/families/not-a-family', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    const text = await page.locator('body').innerText();
    console.log('unknown family body has not-found:', text.includes('Family not found'));
    expect(text).toContain('Family not found');
  });
});