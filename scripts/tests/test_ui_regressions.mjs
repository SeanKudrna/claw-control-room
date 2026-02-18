import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const APP_URL = process.env.UI_TEST_URL || 'http://127.0.0.1:4173/claw-control-room/';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1512, height: 982 } });

try {
  await page.goto(APP_URL, { waitUntil: 'networkidle' });

  await page.locator('text=Insights').first().click();

  const filterChipLabels = await page.$$eval('.chip-row .chip', (chips) => chips.map((chip) => chip.textContent?.trim() ?? ''));
  assert(
    filterChipLabels.every((label) => !/^n\/?a$/i.test(label)),
    `Activity filter chips should not include N/A, got: ${filterChipLabels.join(', ')}`,
  );

  const activityPills = await page.$$eval('.activity-item-meta .tiny-pill', (pills) =>
    pills.map((pill) => pill.textContent?.trim() ?? ''),
  );
  assert(
    activityPills.every((label) => !/^n\/?a$/i.test(label)),
    'Activity feed pills should not display N/A labels.',
  );

  await page.locator('text=Operations').first().click();

  const timelineStatusText = await page.$eval('body', (body) => {
    const node = body.querySelector('.timeline-status');
    return node?.textContent?.trim() ?? null;
  });
  if (timelineStatusText && /Current block highlighted below\./i.test(timelineStatusText)) {
    const currentCount = await page.$$eval('.timeline-item.current', (items) => items.length);
    assert(currentCount > 0, 'Timeline indicates current block is highlighted, but no .timeline-item.current was rendered.');
  }

  console.log('UI regression checks passed');
} finally {
  await page.close();
  await browser.close();
}
