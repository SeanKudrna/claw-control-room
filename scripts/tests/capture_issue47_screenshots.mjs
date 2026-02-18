import { chromium } from 'playwright';

const appUrl = process.env.UI_TEST_URL || 'http://127.0.0.1:4173/claw-control-room/';

const browser = await chromium.launch({ headless: true });
const desktop = await browser.newPage({ viewport: { width: 1512, height: 982 } });
const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });

try {
  await desktop.goto(appUrl, { waitUntil: 'networkidle' });
  await desktop.locator('text=Skills').first().click();
  await desktop.waitForTimeout(500);
  await desktop.screenshot({
    path: 'status/ui-validation/issue47-skills-desktop-tree.png',
    fullPage: true,
  });

  await desktop.locator('.skills-card .skill-node').first().click();
  await desktop.waitForSelector('.skill-modal');
  await desktop.screenshot({
    path: 'status/ui-validation/issue47-skills-desktop-modal.png',
    fullPage: true,
  });

  await mobile.goto(appUrl, { waitUntil: 'networkidle' });
  await mobile.locator('text=Skills').first().click();
  await mobile.waitForTimeout(500);
  await mobile.screenshot({
    path: 'status/ui-validation/issue47-skills-mobile-tree.png',
    fullPage: true,
  });

  await mobile.locator('.skills-card .skill-node').first().click();
  await mobile.waitForSelector('.skill-modal');
  await mobile.screenshot({
    path: 'status/ui-validation/issue47-skills-mobile-modal.png',
    fullPage: true,
  });
} finally {
  await desktop.close();
  await mobile.close();
  await browser.close();
}
