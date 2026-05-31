import { test, expect } from '@playwright/test';

test.describe('Direct Rating MVP Runtime Verification', () => {
  test('click Star button on a fragrance card and verify state transition', async ({ page }) => {
    // 1. Navigate to recommendations
    await page.goto('http://localhost:3000/recommendations', { waitUntil: 'networkidle' });

    // Wait for recommendations to load
    await page.waitForTimeout(3000);

    // 2. Screenshot BEFORE rating
    await page.screenshot({ path: '/tmp/before_rating.png', fullPage: true });

    // 3. Get page content before rating
    const bodyTextBefore = await page.locator('body').innerText();
    console.log('=== BEFORE RATING ===');
    console.log(bodyTextBefore.substring(0, 2000));

    // 4. Check for Star button
    const starButton = page.locator('button:has(svg.lucide-star)');
    const starCount = await starButton.count();
    console.log(`\nStar buttons found: ${starCount}`);

    // 5. Also check for any button containing Star or star icon
    const allStarButtons = page.locator('button:has([data-lucide="star"])');
    const altStarCount = await allStarButtons.count();
    console.log(`Alt Star buttons found: ${altStarCount}`);

    // Check for any star-related elements
    const starElements = page.locator('text=★').or(page.locator('.lucide-star')).or(page.locator('[data-lucide="star"]'));
    const starElemCount = await starElements.count();
    console.log(`Star elements found: ${starElemCount}`);

    // Look for all buttons on the page
    const allButtons = page.locator('button');
    const buttonCount = await allButtons.count();
    console.log(`Total buttons: ${buttonCount}`);
    for (let i = 0; i < buttonCount; i++) {
      const html = await allButtons.nth(i).innerHTML();
      const classes = await allButtons.nth(i).getAttribute('class');
      console.log(`  Button ${i}: class="${classes?.substring(0, 60)}", html contains Star=${html.includes('Star') || html.includes('star')}`);
    }

    // 6. If we found a Star button, click it
    if (starCount > 0) {
      // Click the first Star button
      await starButton.first().click();
      console.log('\nClicked first Star button');
      
      // Wait for the mutation and API call
      await page.waitForTimeout(5000);
      
      // 7. Screenshot AFTER rating
      await page.screenshot({ path: '/tmp/after_rating.png', fullPage: true });

      // 8. Get page content after rating
      const bodyTextAfter = await page.locator('body').innerText();
      console.log('\n=== AFTER RATING ===');
      console.log(bodyTextAfter.substring(0, 2000));
      
      // 9. Check for state change
      const hasTasteInit = bodyTextAfter.includes('Taste Initialising');
      const hasAromatic = bodyTextAfter.includes('Aromatic Constellation');
      const hasPopular = bodyTextAfter.includes('Popular Fragrances');
      const hasColdExploration = bodyTextAfter.includes('Cold Exploration');
      
      console.log(`\n=== STATE TRANSITION CHECK ===`);
      console.log(`Still shows 'Popular Fragrances': ${hasPopular}`);
      console.log(`Still shows 'Cold Exploration': ${hasColdExploration}`);
      console.log(`Shows 'Your Aromatic Constellation': ${hasAromatic}`);
      console.log(`Shows 'Taste Initialising': ${hasTasteInit}`);
      
      if (hasAromatic || hasTasteInit) {
        console.log('\nRESULT: STATE TRANSITION SUCCESSFUL');
      } else if (hasPopular && hasColdExploration) {
        console.log('\nRESULT: STATE DID NOT CHANGE - FEATURE NOT WORKING');
        console.log('The Star click did not trigger a state transition.');
      } else {
        console.log('\nRESULT: PARTIAL OR AMBIGUOUS STATE');
      }
    } else {
      console.log('\nNo Star buttons found! Feature may not be rendering.');
      
      // Check if there are even any fragrance cards
      const articles = page.locator('article');
      const articleCount = await articles.count();
      console.log(`FragranceCard articles found: ${articleCount}`);
      
      // Is the page loading or showing an error?
      const hasError = bodyTextBefore.includes('error') || bodyTextBefore.includes('Error');
      const hasLoading = bodyTextBefore.includes('Loading') || bodyTextBefore.includes('loading');
      console.log(`Page has error: ${hasError}`);
      console.log(`Page is loading: ${hasLoading}`);
    }
  });
});
