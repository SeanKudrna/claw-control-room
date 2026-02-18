import { chromium } from 'playwright';

const appUrl = process.env.UI_TEST_URL || 'http://127.0.0.1:4173/claw-control-room/';

const browser = await chromium.launch({ headless: true });
const desktop = await browser.newPage({ viewport: { width: 1512, height: 982 } });
const mobileContext = await browser.newContext({
  viewport: { width: 390, height: 844 },
  isMobile: true,
  hasTouch: true,
  userAgent:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
});
const mobile = await mobileContext.newPage();

try {
  await desktop.goto(appUrl, { waitUntil: 'networkidle' });
  await desktop.getByRole('tab', { name: 'Skills' }).click({ force: true });
  await desktop.waitForTimeout(500);
  await desktop.screenshot({
    path: 'status/ui-validation/issue48-skills-desktop-tree.png',
    fullPage: true,
  });

  await desktop.locator('.skills-card .skill-node').first().click({ force: true });
  await desktop.waitForSelector('.skill-modal');
  await desktop.screenshot({
    path: 'status/ui-validation/issue48-skills-desktop-modal.png',
    fullPage: true,
  });

  await mobile.goto(appUrl, { waitUntil: 'networkidle' });
  await mobile.getByRole('tab', { name: 'Skills' }).click({ force: true });
  await mobile.waitForTimeout(500);
  await mobile.screenshot({
    path: 'status/ui-validation/issue48-skills-mobile-tree.png',
    fullPage: true,
  });

  await mobile.locator('.skills-card .skill-node').first().click({ force: true });
  await mobile.waitForSelector('.skill-modal');
  await mobile.screenshot({
    path: 'status/ui-validation/issue48-skills-mobile-modal.png',
    fullPage: true,
  });
} finally {
  await desktop.close();
  await mobile.close();
  await mobileContext.close();
  await browser.close();
}
