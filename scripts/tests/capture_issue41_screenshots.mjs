import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1512, height: 982 } });

try {
  await page.goto('http://127.0.0.1:4173/claw-control-room/', { waitUntil: 'networkidle' });

  await page.locator('text=Insights').first().click();
  await page.waitForTimeout(300);
  await page.screenshot({
    path: 'status/ui-validation/issue41-fix-insights-activity-feed-no-na.png',
    fullPage: true,
  });

  await page.locator('text=Operations').first().click();
  await page.waitForTimeout(300);
  await page.screenshot({
    path: 'status/ui-validation/issue41-fix-operations-timeline-current-highlight.png',
    fullPage: true,
  });
} finally {
  await browser.close();
}
