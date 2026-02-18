import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const desktop = await browser.newPage({ viewport: { width: 1512, height: 982 } });
const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });

try {
  await desktop.goto('http://127.0.0.1:4173/claw-control-room/', { waitUntil: 'networkidle' });
  await desktop.locator('text=Skills').first().click();
  await desktop.waitForTimeout(300);
  await desktop.screenshot({
    path: 'status/ui-validation/issue42-skills-tab-desktop.png',
    fullPage: true,
  });

  await mobile.goto('http://127.0.0.1:4173/claw-control-room/', { waitUntil: 'networkidle' });
  await mobile.locator('text=Skills').first().click();
  await mobile.waitForTimeout(300);
  await mobile.screenshot({
    path: 'status/ui-validation/issue42-skills-tab-mobile.png',
    fullPage: true,
  });
} finally {
  await desktop.close();
  await mobile.close();
  await browser.close();
}
