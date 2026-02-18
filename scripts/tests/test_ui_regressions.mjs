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

  const initialScroll = await page.$eval('.skills-tree-map', (node) => ({ left: node.scrollLeft, top: node.scrollTop }));
  await page.hover('.skills-tree-map');
  await page.mouse.down();
  await page.mouse.move(500, 220);
  await page.mouse.up();
  const pannedScroll = await page.$eval('.skills-tree-map', (node) => ({ left: node.scrollLeft, top: node.scrollTop }));
  assert(
    pannedScroll.left !== initialScroll.left || pannedScroll.top !== initialScroll.top,
    `Skill map should pan on drag. Initial=${JSON.stringify(initialScroll)} next=${JSON.stringify(pannedScroll)}`,
  );

  const firstNode = page.locator('.skills-card .skill-node').first();
  const firstNodeTitle = (await firstNode.locator('.skill-node-title').textContent())?.trim() ?? '';
  await firstNode.click();

  await page.waitForSelector('.skill-modal');
  const modalTitle = (await page.textContent('.skill-modal h3'))?.trim() ?? '';
  assert(modalTitle.length > 0, 'Skill modal should render selected skill title.');
  assert.equal(modalTitle, firstNodeTitle, 'Skill modal title should match clicked node title.');

  const modalFieldLabels = await page.$$eval('.skill-detail-grid dt', (nodes) => nodes.map((node) => node.textContent?.trim() ?? ''));
  for (const expectedLabel of ['State', 'Learned', 'Level / Progress', 'Dependencies']) {
    assert(modalFieldLabels.includes(expectedLabel), `Skill modal missing field: ${expectedLabel}`);
  }

  await page.keyboard.press('Escape');
  await page.waitForSelector('.skill-modal', { state: 'detached' });

  await firstNode.click();
  await page.waitForSelector('.skill-modal');
  await page.click('.skill-modal-close');
  await page.waitForSelector('.skill-modal', { state: 'detached' });

  const skillReadability = await page.$$eval('.skills-card .skill-node', (nodes) => {
    const overlaps = [];
    const titleOverflows = [];

    const rects = nodes.map((node, index) => {
      const rect = node.getBoundingClientRect();
      const title = node.querySelector('.skill-node-title');
      if (title && title.scrollWidth - title.clientWidth > 1) {
        titleOverflows.push(index);
      }
      return {
        index,
        tier: Number.parseInt(node.getAttribute('data-tier') ?? '0', 10),
        cx: rect.left + rect.width / 2,
        cy: rect.top + rect.height / 2,
        left: rect.left,
        right: rect.right,
        top: rect.top,
        bottom: rect.bottom,
      };
    });

    for (let i = 0; i < rects.length; i += 1) {
      for (let j = i + 1; j < rects.length; j += 1) {
        const a = rects[i];
        const b = rects[j];
        const intersects = !(a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom);
        if (intersects) overlaps.push([a.index, b.index]);
      }
    }

    const mapRect = document.querySelector('.skills-tree-map')?.getBoundingClientRect();
    const center = mapRect
      ? { x: mapRect.left + mapRect.width / 2, y: mapRect.top + mapRect.height / 2 }
      : { x: 0, y: 0 };

    const avgRadiusByTier = new Map();
    for (const rect of rects) {
      const radius = Math.hypot(rect.cx - center.x, rect.cy - center.y);
      const existing = avgRadiusByTier.get(rect.tier) ?? { total: 0, count: 0 };
      existing.total += radius;
      existing.count += 1;
      avgRadiusByTier.set(rect.tier, existing);
    }

    const tiers = [...avgRadiusByTier.keys()].sort((a, b) => a - b);
    const tierRadiusTrend = tiers.map((tier) => {
      const value = avgRadiusByTier.get(tier);
      return value.total / Math.max(1, value.count);
    });

    const firstNodeElement = nodes[0];
    const title = firstNodeElement?.querySelector('.skill-node-title');
    const lineLayer = document.querySelector('.skills-tree-lines');
    const nodesLayer = document.querySelector('.skills-tree-nodes');
    const titleStyles = title ? window.getComputedStyle(title) : null;

    return {
      overlaps,
      titleOverflows,
      titleFontSizePx: titleStyles ? Number.parseFloat(titleStyles.fontSize) : 0,
      titleFontWeight: titleStyles?.fontWeight ?? '0',
      lineZ: lineLayer ? window.getComputedStyle(lineLayer).zIndex : null,
      nodesZ: nodesLayer ? window.getComputedStyle(nodesLayer).zIndex : null,
      tierRadiusTrend,
      edgeCount: document.querySelectorAll('.skills-tree-lines .skill-link').length,
    };
  });

  assert.equal(skillReadability.overlaps.length, 0, `Skill nodes should not overlap. Got: ${JSON.stringify(skillReadability.overlaps)}`);
  assert.equal(skillReadability.titleOverflows.length, 0, `Skill node titles should not overflow container. Offenders: ${skillReadability.titleOverflows.join(', ')}`);
  assert(skillReadability.titleFontSizePx >= 15, `Skill title font size should be >= 15px; got ${skillReadability.titleFontSizePx}`);
  assert(Number.parseInt(skillReadability.titleFontWeight, 10) >= 700, `Skill title font weight should be bold; got ${skillReadability.titleFontWeight}`);
  assert(skillReadability.edgeCount > 0, 'Skill tree should render dependency connectors.');
  assert(Number.parseInt(skillReadability.nodesZ ?? '0', 10) > Number.parseInt(skillReadability.lineZ ?? '0', 10), 'Skill nodes should render above connector lines.');
  const firstRadius = skillReadability.tierRadiusTrend[0] ?? 0;
  const maxRadius = Math.max(...skillReadability.tierRadiusTrend);
  assert(
    maxRadius - firstRadius >= 180,
    `Skill tiers should branch outward with meaningful radial spread. Got radii: ${skillReadability.tierRadiusTrend.join(', ')}`,
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
