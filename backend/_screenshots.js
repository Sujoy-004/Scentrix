const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

  // 1. Fragrance browser page
  console.log('1. Capturing fragrance browser...');
  await page.goto('http://frontend:3000/fragrances', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);
  // Scroll down a bit to see cards with metadata
  await page.evaluate(() => window.scrollTo(0, 300));
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/app/_screenshots/fragrance-browser.png', fullPage: false });
  console.log('   ✓ fragrance-browser.png');

  // 2. Quiz page
  console.log('2. Capturing quiz...');
  await page.goto('http://frontend:3000/quiz', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/app/_screenshots/quiz.png', fullPage: false });
  console.log('   ✓ quiz.png');

  // 3. Recommendations page
  console.log('3. Capturing recommendations...');
  await page.goto('http://frontend:3000/recommendations', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/app/_screenshots/recommendations.png', fullPage: false });
  console.log('   ✓ recommendations.png');

  await browser.close();
  console.log('Done.');
})();
