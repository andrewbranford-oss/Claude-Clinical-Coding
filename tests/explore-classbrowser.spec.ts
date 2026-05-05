import { test, chromium } from '@playwright/test';
import * as fs from 'fs';

test('explore NHS Classifications Browser with HAR', async ({ }) => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    recordHar: { path: 'classbrowser.har', mode: 'full' },
    viewport: { width: 1280, height: 800 },
  });
  const page = await context.newPage();

  // Navigate to home first, dismiss cookie
  await page.goto('https://classbrowser.nhs.uk/#/');
  await page.waitForLoadState('networkidle');

  const cookieDecline = page.locator('#CybotCookiebotDialogBodyButtonDecline');
  if (await cookieDecline.isVisible()) {
    await cookieDecline.click();
    await page.waitForLoadState('networkidle');
  }

  // Click the ICD-10 link in the nav to navigate into book context
  await page.locator('a:has-text("ICD-10 5th Edition")').first().click();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  // Dismiss license modal via JS
  await page.evaluate(() => {
    const modal = document.getElementById('licenseIcd10Div');
    if (modal) (modal as HTMLElement).style.display = 'none';
    document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
    document.body.classList.remove('modal-open');
  });
  await page.waitForTimeout(500);

  await page.screenshot({ path: 'classbrowser-book.png', fullPage: false });

  // Log computed style of search input to understand why it's hidden
  const searchStyle = await page.evaluate(() => {
    const el = document.getElementById('SearchInput');
    if (!el) return 'NOT FOUND';
    const style = window.getComputedStyle(el);
    return {
      display: style.display,
      visibility: style.visibility,
      opacity: style.opacity,
      height: style.height,
      width: style.width,
      parentDisplay: window.getComputedStyle(el.parentElement!).display,
      parentVisibility: window.getComputedStyle(el.parentElement!).visibility,
    };
  });
  console.log('Search input computed style:', JSON.stringify(searchStyle, null, 2));

  // Force-fill using JavaScript (bypass CSS visibility)
  await page.evaluate(() => {
    const input = document.getElementById('SearchInput') as HTMLInputElement;
    if (input) {
      // Force the element and its parents to be visible
      let el: HTMLElement | null = input;
      while (el) {
        el.style.display = el.style.display === 'none' ? 'block' : el.style.display;
        el.style.visibility = 'visible';
        el.style.opacity = '1';
        el = el.parentElement;
      }
      input.value = 'appendicitis';
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });

  // Now try clicking search button with force
  await page.locator('#SearchButton').click({ force: true });
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);

  await page.screenshot({ path: 'classbrowser-search-results.png', fullPage: false });

  // Finish HAR recording
  await context.close();
  await browser.close();

  // Parse HAR for API calls
  if (fs.existsSync('classbrowser.har')) {
    const har = JSON.parse(fs.readFileSync('classbrowser.har', 'utf8'));
    const apiEntries = har.log.entries
      .filter((e: any) => e.request.url.includes('classbrowser.nhs.uk') &&
        !e.request.url.includes('.js') &&
        !e.request.url.includes('.css') &&
        !e.request.url.includes('.png') &&
        !e.request.url.includes('google') &&
        !e.request.url.includes('cookie'))
      .map((e: any) => ({
        method: e.request.method,
        url: e.request.url,
        status: e.response.status,
        responseBody: e.response.content.text?.slice(0, 500),
        requestHeaders: e.request.headers.filter((h: any) =>
          ['accept', 'content-type', 'referer', 'x-requested-with'].includes(h.name.toLowerCase())
        ),
      }));
    console.log('=== NHS API CALLS FROM HAR ===');
    console.log(JSON.stringify(apiEntries, null, 2));
  }
});
