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

  await page.locator('text=Skills').first().click();
  const skillNodeCount = await page.$$eval('.skills-card .skill-node', (nodes) => nodes.length);
  assert(skillNodeCount > 0, 'Skills tab should render at least one skill node.');

  const skillDetailTitle = await page.$eval('.skill-detail h3', (node) => node.textContent?.trim() ?? '');
  assert(skillDetailTitle.length > 0, 'Skills detail panel should render selected skill title.');

  const skillReadability = await page.$$eval('.skills-card .skill-node', (nodes) => {
    const overlaps = [];
    const titleOverflows = [];

    const rects = nodes.map((node, index) => {
      const rect = node.getBoundingClientRect();
      const title = node.querySelector('.skill-node-title');
      if (title && title.scrollWidth - title.clientWidth > 1) {
        titleOverflows.push(index);
      }
      return { index, left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom };
    });

    for (let i = 0; i < rects.length; i += 1) {
      for (let j = i + 1; j < rects.length; j += 1) {
        const a = rects[i];
        const b = rects[j];
        const intersects = !(a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom);
        if (intersects) overlaps.push([a.index, b.index]);
      }
    }

    const firstNode = nodes[0];
    const title = firstNode?.querySelector('.skill-node-title');
    const detailPanel = document.querySelector('.skill-detail');
    const titleStyles = title ? window.getComputedStyle(title) : null;
    const detailStyles = detailPanel ? window.getComputedStyle(detailPanel) : null;

    return {
      overlaps,
      titleOverflows,
      titleFontSizePx: titleStyles ? Number.parseFloat(titleStyles.fontSize) : 0,
      titleFontWeight: titleStyles?.fontWeight ?? '0',
      detailPaddingTop: detailStyles ? Number.parseFloat(detailStyles.paddingTop) : 0,
      detailGap: detailStyles ? Number.parseFloat(detailStyles.gap) : 0,
    };
  });

  assert.equal(skillReadability.overlaps.length, 0, `Skill nodes should not overlap. Got: ${JSON.stringify(skillReadability.overlaps)}`);
  assert.equal(skillReadability.titleOverflows.length, 0, `Skill node titles should not overflow container. Offenders: ${skillReadability.titleOverflows.join(', ')}`);
  assert(skillReadability.titleFontSizePx >= 15, `Skill title font size should be >= 15px; got ${skillReadability.titleFontSizePx}`);
  assert(Number.parseInt(skillReadability.titleFontWeight, 10) >= 700, `Skill title font weight should be bold; got ${skillReadability.titleFontWeight}`);
  assert(skillReadability.detailPaddingTop >= 14, `Skill detail panel should have readable padding; got ${skillReadability.detailPaddingTop}`);
  assert(skillReadability.detailGap >= 10, `Skill detail panel should have readable spacing gap; got ${skillReadability.detailGap}`);

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
