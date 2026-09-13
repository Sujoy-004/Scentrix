import { test, expect, type Page } from '@playwright/test';

/**
 * Anonymous demo flow — the milestone guardrails for the Scentrix product.
 *
 * Asserts:
 *  - no public route redirects to /auth/login (login surface was removed)
 *  - recommended-fragrance cards navigate to a real /fragrances/<id> detail page
 *  - the rating control submits the ACTUAL selected value (Dislike=3, Neutral=5, Love=9)
 *    on the signed 1–10 scale, and no hardcoded value (e.g. 8) is used
 *  - detail pages degrade gracefully on unknown ids
 *  - the quiz slider communicates the 1–4 / 5 / 6–10 zones
 */

const QUIZ_START_PAYLOAD = {
  status: 'success',
  data: {
    session_id: 'sess-demo-1',
    seed_questions: [
      {
        fragrance_id: 'frag_quiz_a',
        name: 'Neroli Solstice',
        brand: 'Artisan Selection',
        top_notes: ['Bergamot', 'Neroli'],
        accords: ['citrus', 'floral'],
      },
      {
        fragrance_id: 'frag_quiz_b',
        name: 'Amber Dusk',
        brand: 'Maison Noir',
        top_notes: ['Amber', 'Vanilla'],
        accords: ['amber', 'sweet'],
      },
    ],
    rules: {
      min_core_questions: 2,
      max_total_questions: 4,
      medium_extension: 1,
      low_extension: 1,
      confidence_threshold: 0.72,
    },
  },
};

const QUIZ_RESPONSE_PAYLOAD = {
  status: 'success',
  data: { accepted: true },
};

const RECS_PAYLOAD = {
  status: 'success',
  data: [
    { id: 'frag_rec_a', name: 'Tutti Twilly d Hermes', brand: 'Hermes', family: 'floral', rating: 4.2, match_score: 86, top_notes: ['Orange', 'Ginger'], top_accords: ['floral', 'spicy'] },
    { id: 'frag_rec_b', name: 'Chic Blossom', brand: 'Chic', family: 'floral', rating: 3.8, match_score: 74, top_notes: ['Rose', 'Peony'], top_accords: ['floral', 'powdery'] },
    { id: 'frag_rec_c', name: 'Celebre Ice', brand: 'Celebre', family: 'marine', rating: 4.6, match_score: 69, top_notes: ['Sea Salt', 'Mint'], top_accords: ['marine', 'fresh'] },
  ],
  state: 2,
  state_label: 'warm',
};

function mockAnonymousBackend(page: Page): { guestRequests: { body: any }[] } {
  const guestRequests: { body: any }[] = [];

  // Scope all mocks to the API origin (localhost:8000) so Next.js page
  // navigations (localhost:3000) are NEVER intercepted.
  const API = 'http://localhost:8000';

  page.route(`${API}/fragrances/quiz/session/start`, (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(QUIZ_START_PAYLOAD) });
  });
  page.route(`${API}/fragrances/quiz/session/*/answer`, (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(QUIZ_RESPONSE_PAYLOAD) });
  });
  page.route(`${API}/fragrances/quiz/session/*/evaluate`, (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'success',
        data: {
          confidence_score: 0.8,
          confidence_band: 'high',
          extension_required: false,
          additional_questions_target: 0,
          stop_reason: 'confidence_reached',
        },
      }),
    });
  });
  page.route(`${API}/fragrances/quiz/session/*/guest-finalize`, (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(QUIZ_RESPONSE_PAYLOAD) });
  });

  page.route(`${API}/recommendations/guest`, async (route) => {
    guestRequests.push({ body: route.request().postDataJSON() ?? {} });
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(RECS_PAYLOAD) });
  });

  page.route(`${API}/fragrances/frag_rec_*`, (route) => {
    const path = decodeURIComponent(new URL(route.request().url()).pathname);
    const id = path.split('/').pop() ?? '';
    const match = RECS_PAYLOAD.data.find((r) => r.id === id);
    if (match) {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          data: {
            ...match,
            year: 2023,
            concentration: 'EDP',
            gender_label: 'Unisex',
            description: 'A demo fragrance used by the anonymous-flow test.',
            top_notes: match.top_notes,
            middle_notes: ['Iris', 'Vetiver'],
            base_notes: ['Musk'],
            accords: match.top_accords,
          },
        }),
      });
    } else {
      route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ status: 'error', detail: 'Fragrance not found' }) });
    }
  });

  page.route(`${API}/fragrances/catalog?*`, (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'success', data: { items: RECS_PAYLOAD.data, total: 3, limit: 20, offset: 0 } }),
    });
  });

  return { guestRequests };
}

test.describe('anonymous demo flow', () => {
  test.setTimeout(150_000);
  test('home, quiz, families and recommendations never redirect to auth', async ({ page }) => {
    mockAnonymousBackend(page);
    for (const route of ['/', '/quiz', '/families', '/recommendations']) {
      const response = await page.goto(route, { waitUntil: 'domcontentloaded' });
      expect(response?.status()).toBeLessThan(400);
      expect(page.url()).not.toContain('/auth/login');
    }
  });

  test('fragrance cards navigate to the detail page', async ({ page }) => {
    mockAnonymousBackend(page);
    await page.goto('/recommendations', { waitUntil: 'domcontentloaded' });
    await page.getByText('Tutti Twilly d Hermes').first().waitFor({ timeout: 15000 });

    const card = page.getByText('Tutti Twilly d Hermes').first();
    await card.scrollIntoViewIfNeeded();
    await card.click();

    await page.waitForURL(/\/fragrances\/frag_rec_a$/, { timeout: 15000 });
    await expect(page.getByRole('heading', { name: 'Tutti Twilly d Hermes' })).toBeVisible();
  });

  test('rating control submits the actual selected value (3 / 5 / 9), never a hardcoded 8', async ({ page }) => {
    const { guestRequests } = mockAnonymousBackend(page);
    await page.goto('/recommendations', { waitUntil: 'domcontentloaded' });

    await page.getByText('Tutti Twilly d Hermes').first().waitFor({ timeout: 15000 });

    // Dismiss the cookie banner if present — it can intercept pointer events.
    const closeBanner = page.locator('button', { hasText: /Close and decline cookies|Accept/i }).first();
    if (await closeBanner.isVisible({ timeout: 2000 }).catch(() => false)) {
      await closeBanner.click();
    }

    // Rate one card at a time. Each rating bumps quizResponses.length → refetch
    // → the recommendations grid is AnimatePresence-keyed on isRefetching, so the
    // whole card list unmounts/remounts. Use locator.evaluate() to dispatch clicks
    // directly on the correct DOM node (bypassing Playwright's pointer-position-
    // based click which can fail during layout shifts).
    const waitForRatingsRequest = (n: number) =>
      expect
        .poll(() => {
          const last = guestRequests[guestRequests.length - 1];
          return last?.body?.ratings?.length ?? 0;
        }, { timeout: 15000 })
        .toBe(n);
    const settle = () => page.waitForTimeout(1000);

    // Card 1 — Tutti Twilly — Dislike (3)
    await page.getByRole('button', { name: /^Dislike/ }).first().evaluate(
      (btn) => (btn as HTMLButtonElement).click(),
    );
    await waitForRatingsRequest(1);
    await settle();

    // Card 2 — Chic Blossom — Neutral (5). After card 1 is rated its controls
    // are removed, so "first" now targets the remaining top card (Chic Blossom).
    await page.getByRole('button', { name: /^Neutral/ }).first().evaluate(
      (btn) => (btn as HTMLButtonElement).click(),
    );
    await waitForRatingsRequest(2);
    await settle();

    // Card 3 — Celebre Ice — Love (9). Only one set of controls remains.
    await page.getByRole('button', { name: /^Love/ }).first().evaluate(
      (btn) => (btn as HTMLButtonElement).click(),
    );
    await waitForRatingsRequest(3);

    const last = guestRequests[guestRequests.length - 1];
    const ratings = last.body.ratings;
    const byId = Object.fromEntries(ratings.map((r: { fragrance_id: string; rating: number }) => [r.fragrance_id, r.rating]));
    expect(byId).toMatchObject({ frag_rec_a: 3, frag_rec_b: 5, frag_rec_c: 9 });
    expect(Object.values(byId).every((v) => [3, 5, 9].includes(v as number))).toBe(true);
    expect(Object.values(byId)).not.toContain(8);
  });

  test('unknown fragrance ids render a graceful not-found state', async ({ page }) => {
    mockAnonymousBackend(page);
    page.route('http://localhost:8000/fragrances/does-not-exist', (route) => {
      route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ status: 'error', detail: 'Fragrance not found' }) });
    });

    await page.goto('/fragrances/does-not-exist', { waitUntil: 'domcontentloaded' });
    await expect(page.getByText('Fragrance not found')).toBeVisible({ timeout: 15000 });
  });

  test('quiz slider communicates the 1–4 / 5 / 6–10 zones', async ({ page }) => {
    mockAnonymousBackend(page);
    await page.goto('/quiz', { waitUntil: 'domcontentloaded' });

    await expect(page.getByText('1–4 Dislike')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('5 Neutral')).toBeVisible();
    await expect(page.getByText('6–10 Like')).toBeVisible();

    const slider = page.locator('input[type="range"]').first();
    await expect(slider).toHaveValue('5');
  });
});