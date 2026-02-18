import { chromium } from 'playwright';

const label = process.argv[2] || 'after';
const appUrl = process.env.UI_TEST_URL || 'http://127.0.0.1:4173/claw-control-room/';

const browser = await chromium.launch({ headless: true });
const desktop = await browser.newPage({ viewport: { width: 1512, height: 982 } });
const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });

try {
  await desktop.goto(appUrl, { waitUntil: 'networkidle' });
  await desktop.locator('text=Skills').first().click();
  await desktop.waitForTimeout(600);
  await desktop.screenshot({
    path: `status/ui-validation/issue44-skills-${label}-desktop.png`,
    fullPage: true,
  });

  await mobile.goto(appUrl, { waitUntil: 'networkidle' });
  await mobile.locator('text=Skills').first().click();
  await mobile.waitForTimeout(600);
  await mobile.screenshot({
    path: `status/ui-validation/issue44-skills-${label}-mobile.png`,
    fullPage: true,
  });
} finally {
  await desktop.close();
  await mobile.close();
  await browser.close();
}
