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
  await desktop.keyboard.press(`${process.platform === 'darwin' ? 'Meta' : 'Control'}+KeyK`);
  await desktop.fill('.command-center-input', 'diagnostics');
  await desktop.screenshot({
    path: 'status/ui-validation/issue51-command-center-desktop.png',
    fullPage: true,
  });

  await desktop.keyboard.press('Escape');
  await desktop.locator('.command-center-trigger').click();
  await desktop.fill('.command-center-input', 'Open current diagnostics view');
  await desktop.keyboard.press('Enter');
  await desktop.waitForSelector('#refresh-diagnostics');
  await desktop.screenshot({
    path: 'status/ui-validation/issue51-refresh-diagnostics-desktop.png',
    fullPage: true,
  });

  await mobile.goto(appUrl, { waitUntil: 'networkidle' });
  await mobile.locator('.command-center-trigger').click({ force: true });
  await mobile.fill('.command-center-input', 'stale');
  await mobile.screenshot({
    path: 'status/ui-validation/issue51-command-center-mobile.png',
    fullPage: true,
  });

  await mobile.keyboard.press('Escape');
  await mobile.locator('.command-center-trigger').click({ force: true });
  await mobile.fill('.command-center-input', 'Open current diagnostics view');
  await mobile.keyboard.press('Enter');
  await mobile.waitForSelector('#refresh-diagnostics');
  await mobile.screenshot({
    path: 'status/ui-validation/issue51-refresh-diagnostics-mobile.png',
    fullPage: true,
  });
} finally {
  await desktop.close();
  await mobile.close();
  await mobileContext.close();
  await browser.close();
}
