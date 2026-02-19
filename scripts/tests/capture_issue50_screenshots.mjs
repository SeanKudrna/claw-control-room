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

  await desktop.locator('[data-map-control="fit-reset"]').click({ force: true });
  await desktop.waitForFunction(
    () => Number.parseFloat(document.querySelector('.skills-tree-map')?.getAttribute('data-map-zoom') ?? '1') < 0.98,
  );

  await desktop.screenshot({
    path: 'status/ui-validation/issue50-skills-desktop-tree-fit.png',
    fullPage: true,
  });

  await desktop.locator('[data-map-control="fit-reset"]').click({ force: true });
  await desktop.waitForFunction(
    () => Math.abs(Number.parseFloat(document.querySelector('.skills-tree-map')?.getAttribute('data-map-zoom') ?? '1') - 1) <= 0.02,
  );

  await desktop.locator('.skills-card .skill-node').nth(1).click({ force: true });
  await desktop.waitForSelector('.skill-modal');
  await desktop.screenshot({
    path: 'status/ui-validation/issue50-skills-desktop-modal-meaning.png',
    fullPage: true,
  });

  await mobile.goto(appUrl, { waitUntil: 'networkidle' });
  await mobile.getByRole('tab', { name: 'Skills' }).click({ force: true });

  await mobile.locator('[data-map-control="fit-reset"]').click({ force: true });
  await mobile.waitForFunction(
    () => Number.parseFloat(document.querySelector('.skills-tree-map')?.getAttribute('data-map-zoom') ?? '1') < 0.98,
  );

  await mobile.screenshot({
    path: 'status/ui-validation/issue50-skills-mobile-tree-fit.png',
    fullPage: true,
  });

  await mobile.locator('[data-map-control="fit-reset"]').click({ force: true });
  await mobile.waitForFunction(
    () => Math.abs(Number.parseFloat(document.querySelector('.skills-tree-map')?.getAttribute('data-map-zoom') ?? '1') - 1) <= 0.02,
  );

  await mobile.locator('.skills-card .skill-node').nth(1).click({ force: true });
  await mobile.waitForSelector('.skill-modal');
  await mobile.screenshot({
    path: 'status/ui-validation/issue50-skills-mobile-modal-meaning.png',
    fullPage: true,
  });
} finally {
  await desktop.close();
  await mobile.close();
  await mobileContext.close();
  await browser.close();
}
