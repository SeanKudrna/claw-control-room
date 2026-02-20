import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const APP_URL = process.env.UI_TEST_URL || 'http://127.0.0.1:4173/claw-control-room/';

async function getLayoutSignature(page) {
  return page.$$eval('.skills-card .skill-node', (nodes) =>
    nodes
      .map((node) => ({
        id: node.getAttribute('data-node-id') ?? '',
        left: node.style.left,
        top: node.style.top,
        depth: node.getAttribute('data-layout-depth') ?? '',
        root: node.getAttribute('data-layout-root') ?? '',
        branch: node.getAttribute('data-layout-branch') ?? '',
      }))
      .sort((a, b) => a.id.localeCompare(b.id)),
  );
}

async function dragMapWithMouse(page, selector) {
  const target = page.locator(selector);
  const box = await target.boundingBox();
  assert(box, `Expected a bounding box for ${selector}`);

  const startX = box.x + box.width * 0.72;
  const startY = box.y + box.height * 0.66;
  const endX = startX - Math.min(240, box.width * 0.3);
  const endY = startY - Math.min(170, box.height * 0.26);

  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(endX, endY);
  await page.mouse.up();
}

async function dragMapWithTouch(page, selector) {
  const target = page.locator(selector);
  const box = await target.boundingBox();
  assert(box, `Expected a bounding box for ${selector}`);

  const startX = box.x + box.width * 0.72;
  const startY = box.y + box.height * 0.68;
  const endX = startX - Math.min(180, box.width * 0.32);
  const endY = startY - Math.min(140, box.height * 0.24);

  const base = {
    pointerId: 71,
    pointerType: 'touch',
    isPrimary: true,
    button: 0,
  };

  await page.dispatchEvent(selector, 'pointerdown', {
    ...base,
    buttons: 1,
    clientX: startX,
    clientY: startY,
  });

  await page.dispatchEvent(selector, 'pointermove', {
    ...base,
    buttons: 1,
    clientX: endX,
    clientY: endY,
  });

  await page.dispatchEvent(selector, 'pointerup', {
    ...base,
    buttons: 0,
    clientX: endX,
    clientY: endY,
  });
}

async function readMapMetrics(page, selector = '.skills-tree-map') {
  return page.$eval(selector, (node) => ({
    zoom: Number.parseFloat(node.getAttribute('data-map-zoom') ?? '1'),
    left: node.scrollLeft,
    top: node.scrollTop,
    clientWidth: node.clientWidth,
    clientHeight: node.clientHeight,
    scrollWidth: node.scrollWidth,
    scrollHeight: node.scrollHeight,
    maxLeft: Math.max(0, node.scrollWidth - node.clientWidth),
    maxTop: Math.max(0, node.scrollHeight - node.clientHeight),
  }));
}

const browser = await chromium.launch({ headless: true });
const desktopPage = await browser.newPage({ viewport: { width: 1512, height: 982 } });

let mobileContext;
let mobilePage;

try {
  await desktopPage.goto(APP_URL, { waitUntil: 'networkidle' });

  await desktopPage.keyboard.press(`${process.platform === 'darwin' ? 'Meta' : 'Control'}+KeyK`);
  await desktopPage.waitForSelector('.command-center-modal');
  await desktopPage.fill('.command-center-input', 'Force refresh now');
  await desktopPage.keyboard.press('Enter');
  await desktopPage.waitForSelector('.command-center-modal', { state: 'detached' });

  await desktopPage.keyboard.press(`${process.platform === 'darwin' ? 'Meta' : 'Control'}+KeyK`);
  await desktopPage.waitForSelector('.command-center-modal');
  await desktopPage.fill('.command-center-input', 'Open current diagnostics view');
  await desktopPage.keyboard.press('Enter');
  await desktopPage.waitForSelector('#refresh-diagnostics');

  const diagnosticsContract = await desktopPage.$eval('#refresh-diagnostics', (node) => {
    const terms = [...node.querySelectorAll('dt')].map((term) => term.textContent?.trim() ?? '');
    const values = [...node.querySelectorAll('dd')].map((value) => value.textContent?.trim() ?? '');
    return {
      terms,
      hasStateBadge: !!node.querySelector('.tiny-pill'),
      hasFootnote: !!node.querySelector('.refresh-diagnostics-footnote'),
      valueCount: values.length,
    };
  });
  for (const expected of ['Last outcome', 'Source mode', 'Freshness', 'Age', 'Last error']) {
    assert(diagnosticsContract.terms.includes(expected), `Refresh diagnostics missing field: ${expected}`);
  }
  assert(diagnosticsContract.hasStateBadge, 'Refresh diagnostics panel should include stale/fresh state badge.');
  assert(diagnosticsContract.hasFootnote, 'Refresh diagnostics panel should include compact state footnote.');
  assert(diagnosticsContract.valueCount >= 5, 'Refresh diagnostics panel should include diagnostic values.');

  await desktopPage.getByRole('tab', { name: 'Insights' }).click({ force: true });

  const filterChipLabels = await desktopPage.$$eval('.chip-row .chip', (chips) => chips.map((chip) => chip.textContent?.trim() ?? ''));
  assert(
    filterChipLabels.every((label) => !/^n\/?a$/i.test(label)),
    `Activity filter chips should not include N/A, got: ${filterChipLabels.join(', ')}`,
  );

  const activityPills = await desktopPage.$$eval('.activity-item-meta .tiny-pill', (pills) =>
    pills.map((pill) => pill.textContent?.trim() ?? ''),
  );
  assert(
    activityPills.every((label) => !/^n\/?a$/i.test(label)),
    'Activity feed pills should not display N/A labels.',
  );

  await desktopPage.getByRole('tab', { name: 'Skills' }).click({ force: true });
  const skillNodeCount = await desktopPage.$$eval('.skills-card .skill-node', (nodes) => nodes.length);
  assert(skillNodeCount > 0, 'Skills tab should render at least one skill node.');

  const fullSurfaceMetrics = await desktopPage.$eval('.skills-card', (card) => {
    const map = card.querySelector('.skills-tree-map');
    const dashboardGrid = document.querySelector('.dashboard-grid');
    const cardRect = card.getBoundingClientRect();
    const mapRect = map?.getBoundingClientRect();
    const viewportHeight = window.innerHeight;

    if (!map || !mapRect) {
      return {
        ok: false,
        reason: 'Missing .skills-tree-map element',
      };
    }

    return {
      ok: true,
      surfaceMode: card.getAttribute('data-skills-surface') ?? '',
      mapMode: map.getAttribute('data-map-surface') ?? '',
      mapHeightRatio: mapRect.height / Math.max(1, cardRect.height),
      mapWidthRatio: mapRect.width / Math.max(1, cardRect.width),
      mapViewportHeightRatio: mapRect.height / Math.max(1, viewportHeight),
      gridHeightRatio: dashboardGrid
        ? cardRect.height / Math.max(1, dashboardGrid.getBoundingClientRect().height)
        : 0,
      isOverflowPannable: map.scrollWidth > map.clientWidth + 1 || map.scrollHeight > map.clientHeight + 1,
    };
  });

  assert.equal(fullSurfaceMetrics.ok, true, fullSurfaceMetrics.reason ?? 'Skills map surface metrics unavailable.');
  assert.equal(fullSurfaceMetrics.surfaceMode, 'full-tab', 'Skills tab should mark full-tab surface mode.');
  assert.equal(fullSurfaceMetrics.mapMode, 'full-tab', 'Skills map should mark full-tab pannable mode.');
  assert(
    fullSurfaceMetrics.mapHeightRatio >= 0.72,
    `Skills map should dominate tab height. Ratio=${fullSurfaceMetrics.mapHeightRatio.toFixed(3)}`,
  );
  assert(
    fullSurfaceMetrics.mapWidthRatio >= 0.96,
    `Skills map should use full tab width. Ratio=${fullSurfaceMetrics.mapWidthRatio.toFixed(3)}`,
  );
  assert(
    fullSurfaceMetrics.mapViewportHeightRatio >= 0.5,
    `Skills map should occupy substantial viewport height. Ratio=${fullSurfaceMetrics.mapViewportHeightRatio.toFixed(3)}`,
  );
  assert(
    fullSurfaceMetrics.gridHeightRatio >= 0.95,
    `Skills surface should occupy the full tab content grid. Ratio=${fullSurfaceMetrics.gridHeightRatio.toFixed(3)}`,
  );
  assert(fullSurfaceMetrics.isOverflowPannable, 'Skills map should remain overflow-pannable.');

  const nodeDomainContract = await desktopPage.$$eval('.skills-card .skill-node', (nodes) => {
    const ids = nodes.map((node) => node.getAttribute('data-node-id') ?? '');
    const progressLabels = nodes.map((node) => node.querySelector('.skill-node-progress')?.textContent?.trim() ?? '');
    const functionCopy = nodes.map((node) => node.querySelector('.skill-node-function')?.textContent?.trim() ?? '');
    const nextCopy = nodes.map((node) => node.querySelector('.skill-node-meta')?.textContent?.trim() ?? '');
    return {
      uniqueCount: new Set(ids).size,
      totalCount: ids.length,
      progressLabels,
      functionCopy,
      nextCopy,
    };
  });
  assert.equal(
    nodeDomainContract.uniqueCount,
    nodeDomainContract.totalCount,
    'Skills graph should render a single node per domain (no duplicate domain cards).',
  );
  assert(
    nodeDomainContract.progressLabels.every((label) => /^Tier\s+\d+\s*\/\s*\d+$/i.test(label)),
    `Each skill node should show concise tier progression (e.g., Tier 3/5). Got: ${nodeDomainContract.progressLabels.join(', ')}`,
  );
  assert(
    nodeDomainContract.functionCopy.every((label) => label.length >= 12),
    `Each skill node should include current-function copy. Got: ${nodeDomainContract.functionCopy.join(' | ')}`,
  );
  assert(
    nodeDomainContract.nextCopy.every((label) => /^Next:/i.test(label)),
    `Each skill node should include next level-up meaning. Got: ${nodeDomainContract.nextCopy.join(' | ')}`,
  );

  const controlContract = await desktopPage.$$eval('.skills-map-controls [data-map-control]', (controls) =>
    controls.map((control) => ({
      id: control.getAttribute('data-map-control') ?? '',
      text: (control.textContent ?? '').trim(),
    })),
  );
  const controlIds = new Set(controlContract.map((control) => control.id));
  for (const expected of ['zoom-out', 'zoom-in', 'fit-reset']) {
    assert(controlIds.has(expected), `Missing expected skills map control: ${expected}`);
  }

  const mapMetricsBeforeZoom = await readMapMetrics(desktopPage);
  assert.equal(mapMetricsBeforeZoom.zoom, 1, 'Skills map should default to 100% zoom.');

  await desktopPage.locator('[data-map-control="zoom-in"]').click({ force: true });
  await desktopPage.waitForFunction(
    () => Number.parseFloat(document.querySelector('.skills-tree-map')?.getAttribute('data-map-zoom') ?? '1') > 1.05,
  );

  const mapMetricsAfterZoomIn = await readMapMetrics(desktopPage);
  assert(
    mapMetricsAfterZoomIn.zoom > mapMetricsBeforeZoom.zoom + 0.05,
    `Zoom-in control should increase map zoom. Before=${mapMetricsBeforeZoom.zoom} after=${mapMetricsAfterZoomIn.zoom}`,
  );
  assert(
    mapMetricsAfterZoomIn.scrollWidth > mapMetricsBeforeZoom.scrollWidth,
    'Zoom-in should increase scrollable map width.',
  );

  await desktopPage.locator('[data-map-control="fit-reset"]').click({ force: true });
  await desktopPage.waitForFunction(() => {
    const map = document.querySelector('.skills-tree-map');
    if (!map) return false;
    const zoom = Number.parseFloat(map.getAttribute('data-map-zoom') ?? '1');
    return zoom < 0.98;
  });

  const fitMetrics = await readMapMetrics(desktopPage);
  assert(
    fitMetrics.zoom <= 0.98,
    `Fit control should reduce zoom to expose broader map context. zoom=${fitMetrics.zoom}`,
  );

  await desktopPage.locator('[data-map-control="fit-reset"]').click({ force: true });
  await desktopPage.waitForFunction(() => {
    const map = document.querySelector('.skills-tree-map');
    if (!map) return false;
    const zoom = Number.parseFloat(map.getAttribute('data-map-zoom') ?? '0');
    return Math.abs(zoom - 1) <= 0.02;
  });
  await desktopPage.waitForFunction(() => {
    const map = document.querySelector('.skills-tree-map');
    if (!map) return false;
    const expectedLeft = Math.max(0, (map.scrollWidth - map.clientWidth) / 2);
    return Math.abs(map.scrollLeft - expectedLeft) <= Math.max(12, map.clientWidth * 0.06);
  });

  const mapMetricsAfterReset = await readMapMetrics(desktopPage);
  assert(
    Math.abs(mapMetricsAfterReset.zoom - 1) <= 0.02,
    `Fit/reset control should return to 100% zoom. zoom=${mapMetricsAfterReset.zoom}`,
  );
  const expectedCenterLeft = Math.max(0, (mapMetricsAfterReset.scrollWidth - mapMetricsAfterReset.clientWidth) / 2);
  const expectedCenterTop = Math.max(0, (mapMetricsAfterReset.scrollHeight - mapMetricsAfterReset.clientHeight) / 2);
  assert(
    Math.abs(mapMetricsAfterReset.left - expectedCenterLeft) <= Math.max(12, mapMetricsAfterReset.clientWidth * 0.04),
    `Reset view should recenter horizontally. left=${mapMetricsAfterReset.left} expected≈${expectedCenterLeft}`,
  );
  assert(
    Math.abs(mapMetricsAfterReset.top - expectedCenterTop) <= Math.max(12, mapMetricsAfterReset.clientHeight * 0.04),
    `Reset view should recenter vertically. top=${mapMetricsAfterReset.top} expected≈${expectedCenterTop}`,
  );

  const initialLayoutSignature = await getLayoutSignature(desktopPage);
  assert(initialLayoutSignature.length > 0, 'Skills layout signature should not be empty.');

  const initialScroll = await readMapMetrics(desktopPage);
  await dragMapWithMouse(desktopPage, '.skills-tree-map');
  const pannedScroll = await readMapMetrics(desktopPage);
  assert(
    pannedScroll.left !== initialScroll.left || pannedScroll.top !== initialScroll.top,
    `Skill map should pan on drag. Initial=${JSON.stringify(initialScroll)} next=${JSON.stringify(pannedScroll)}`,
  );
  assert(
    pannedScroll.left >= 0 && pannedScroll.left <= pannedScroll.maxLeft + 0.5,
    `Panned horizontal position should stay within map bounds. left=${pannedScroll.left} max=${pannedScroll.maxLeft}`,
  );
  assert(
    pannedScroll.top >= 0 && pannedScroll.top <= pannedScroll.maxTop + 0.5,
    `Panned vertical position should stay within map bounds. top=${pannedScroll.top} max=${pannedScroll.maxTop}`,
  );

  const firstNode = desktopPage.locator('.skills-card .skill-node').first();
  const firstNodeTitle = (await firstNode.locator('.skill-node-title').textContent())?.trim() ?? '';
  await firstNode.click({ force: true });

  await desktopPage.waitForSelector('.skill-modal');
  const modalTitle = (await desktopPage.textContent('.skill-modal h3'))?.trim() ?? '';
  assert(modalTitle.length > 0, 'Skill modal should render selected skill title.');
  assert.equal(modalTitle, firstNodeTitle, 'Skill modal title should match clicked node title.');

  const modalFieldLabels = await desktopPage.$$eval('.skill-detail-grid dt', (nodes) => nodes.map((node) => node.textContent?.trim() ?? ''));
  for (const expectedLabel of ['State', 'Learned', 'Signal', 'Dependencies']) {
    assert(modalFieldLabels.includes(expectedLabel), `Skill modal missing field: ${expectedLabel}`);
  }

  const modalMeaningHeadings = await desktopPage.$$eval('.skill-meaning-card h4', (nodes) => nodes.map((node) => node.textContent?.trim() ?? ''));
  for (const heading of ['Current function', 'Next level-up meaning']) {
    assert(modalMeaningHeadings.includes(heading), `Skill modal meaning card missing: ${heading}`);
  }

  const requirementContract = await desktopPage.$eval('.skill-requirements-panel', (panel) => {
    const heading = panel.querySelector('.skill-requirements-header h4')?.textContent?.trim() ?? '';
    const entries = [...panel.querySelectorAll('.skill-requirement')].map((entry) => ({
      label: entry.querySelector('.skill-requirement-label')?.textContent?.trim() ?? '',
      state: entry.querySelector('.skill-requirement-state')?.textContent?.trim() ?? '',
      detail: entry.querySelector('.skill-requirement-copy .muted')?.textContent?.trim() ?? '',
    }));

    return {
      heading,
      count: entries.length,
      entries,
    };
  });
  assert.equal(requirementContract.heading, 'Locked requirements', 'Skill modal should include locked-requirements heading.');
  assert(requirementContract.count >= 1, 'Skill modal should list at least one locked requirement row.');
  assert(
    requirementContract.entries.every((entry) => entry.label.length > 0 && entry.state.length > 0 && entry.detail.length > 0),
    `Skill requirement rows should include label/state/detail. Got: ${JSON.stringify(requirementContract.entries)}`,
  );

  const tierLadderState = await desktopPage.$eval('.skill-tier-panel', (panel) => {
    const steps = [...panel.querySelectorAll('.skill-tier-step')];
    const current = panel.querySelectorAll('.skill-tier-step.current').length;
    const next = panel.querySelectorAll('.skill-tier-step.next').length;
    const complete = panel.querySelectorAll('.skill-tier-step.complete').length;
    const summary = panel.querySelector('.skill-tier-pill')?.textContent?.trim() ?? '';
    return {
      stepCount: steps.length,
      current,
      next,
      complete,
      summary,
    };
  });
  assert.equal(tierLadderState.stepCount, 5, 'Skill modal tier ladder should render tier definitions 1..5.');
  assert(tierLadderState.current <= 1, 'Skill modal should have at most one current tier highlight.');
  assert(
    tierLadderState.current === 1 || tierLadderState.next >= 1,
    'Skill modal should indicate current tier or next unlock state.',
  );
  assert(
    /Tier\s+\d+\s*\/\s*5/i.test(tierLadderState.summary),
    `Skill modal summary should show Tier x/5 progression. Got: ${tierLadderState.summary}`,
  );

  await desktopPage.keyboard.press('Escape');
  await desktopPage.waitForSelector('.skill-modal', { state: 'detached' });

  await firstNode.click({ force: true });
  await desktopPage.waitForSelector('.skill-modal');
  await desktopPage.click('.skill-modal-close');
  await desktopPage.waitForSelector('.skill-modal', { state: 'detached' });

  const skillReadability = await desktopPage.$$eval('.skills-card .skill-node', (nodes) => {
    const overlaps = [];
    const titleOverflows = [];
    const clippedNodes = [];

    const canvas = document.querySelector('.skills-tree-canvas');
    const map = document.querySelector('.skills-tree-map');
    const canvasWidth = canvas?.clientWidth ?? 0;
    const canvasHeight = canvas?.clientHeight ?? 0;
    const centerX = canvasWidth / 2;
    const centerY = canvasHeight / 2;

    const rects = nodes.map((node, index) => {
      const cx = Number.parseFloat(node.style.left || '0');
      const cy = Number.parseFloat(node.style.top || '0');
      const width = node.clientWidth;
      const height = node.clientHeight;

      const title = node.querySelector('.skill-node-title');
      if (title && title.scrollWidth - title.clientWidth > 1) {
        titleOverflows.push(index);
      }

      const left = cx - width / 2;
      const right = cx + width / 2;
      const top = cy - height / 2;
      const bottom = cy + height / 2;

      if (left < 0 || right > canvasWidth || top < 0 || bottom > canvasHeight) {
        clippedNodes.push(index);
      }

      return {
        index,
        id: node.getAttribute('data-node-id') ?? '',
        depth: Number.parseInt(node.getAttribute('data-layout-depth') ?? '0', 10),
        cx,
        cy,
        left,
        right,
        top,
        bottom,
      };
    });

    for (let i = 0; i < rects.length; i += 1) {
      for (let j = i + 1; j < rects.length; j += 1) {
        const a = rects[i];
        const b = rects[j];
        const intersects = !(a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom);
        if (intersects) overlaps.push([a.id, b.id]);
      }
    }

    const avgRadiusByDepth = new Map();
    for (const rect of rects) {
      const radius = Math.hypot(rect.cx - centerX, rect.cy - centerY);
      const existing = avgRadiusByDepth.get(rect.depth) ?? { total: 0, count: 0 };
      existing.total += radius;
      existing.count += 1;
      avgRadiusByDepth.set(rect.depth, existing);
    }

    const depthTrend = [...avgRadiusByDepth.keys()]
      .sort((a, b) => a - b)
      .map((depth) => {
        const value = avgRadiusByDepth.get(depth);
        return {
          depth,
          radius: value.total / Math.max(1, value.count),
        };
      });

    const firstNodeElement = nodes[0];
    const title = firstNodeElement?.querySelector('.skill-node-title');
    const lineLayer = document.querySelector('.skills-tree-lines');
    const nodesLayer = document.querySelector('.skills-tree-nodes');
    const titleStyles = title ? window.getComputedStyle(title) : null;

    return {
      overlaps,
      titleOverflows,
      clippedNodes,
      titleFontSizePx: titleStyles ? Number.parseFloat(titleStyles.fontSize) : 0,
      titleFontWeight: titleStyles?.fontWeight ?? '0',
      lineZ: lineLayer ? window.getComputedStyle(lineLayer).zIndex : null,
      nodesZ: nodesLayer ? window.getComputedStyle(nodesLayer).zIndex : null,
      depthTrend,
      edgeCount: document.querySelectorAll('.skills-tree-lines .skill-link').length,
      mapPannable: map ? map.scrollWidth > map.clientWidth || map.scrollHeight > map.clientHeight : false,
    };
  });

  assert.equal(skillReadability.overlaps.length, 0, `Skill nodes should not overlap. Got: ${JSON.stringify(skillReadability.overlaps)}`);
  assert.equal(skillReadability.titleOverflows.length, 0, `Skill node titles should not overflow container. Offenders: ${skillReadability.titleOverflows.join(', ')}`);
  assert.equal(skillReadability.clippedNodes.length, 0, `Skill nodes should stay inside canvas bounds. Offenders: ${skillReadability.clippedNodes.join(', ')}`);
  assert(skillReadability.titleFontSizePx >= 15, `Skill title font size should be >= 15px; got ${skillReadability.titleFontSizePx}`);
  assert(Number.parseInt(skillReadability.titleFontWeight, 10) >= 700, `Skill title font weight should be bold; got ${skillReadability.titleFontWeight}`);
  assert(skillReadability.edgeCount > 0, 'Skill tree should render dependency connectors.');
  assert(Number.parseInt(skillReadability.nodesZ ?? '0', 10) > Number.parseInt(skillReadability.lineZ ?? '0', 10), 'Skill nodes should render above connector lines.');
  assert(skillReadability.mapPannable, 'Skill map should remain pannable with overflow.');
  assert(skillReadability.depthTrend.length >= 2, 'Skill layout should expose at least two depth layers.');
  for (let index = 1; index < skillReadability.depthTrend.length; index += 1) {
    const prev = skillReadability.depthTrend[index - 1];
    const next = skillReadability.depthTrend[index];
    assert(
      next.radius - prev.radius >= 70,
      `Skill dependency depth rings should expand outward. Trend=${JSON.stringify(skillReadability.depthTrend)}`,
    );
  }

  await desktopPage.reload({ waitUntil: 'networkidle' });
  const skillsStillVisibleAfterReload = await desktopPage
    .locator('.skills-card .skill-node')
    .first()
    .isVisible()
    .catch(() => false);
  if (!skillsStillVisibleAfterReload) {
    await desktopPage.getByRole('tab', { name: 'Skills' }).click({ force: true });
  }
  await desktopPage.waitForSelector('.skills-card .skill-node');
  const postReloadLayoutSignature = await getLayoutSignature(desktopPage);
  assert.deepEqual(
    postReloadLayoutSignature,
    initialLayoutSignature,
    'Skill node placement should remain deterministic across refreshes (no layout jitter).',
  );

  mobileContext = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    userAgent:
      'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  });
  mobilePage = await mobileContext.newPage();

  await mobilePage.goto(APP_URL, { waitUntil: 'networkidle' });

  await mobilePage.locator('.command-center-trigger').click({ force: true });
  await mobilePage.waitForSelector('.command-center-modal');
  await mobilePage.fill('.command-center-input', 'zzzz-no-match');
  const emptyVisible = await mobilePage.locator('.command-center-empty').isVisible();
  assert(emptyVisible, 'Command center should render empty-state UX when no matches exist.');
  await mobilePage.keyboard.press('Escape');
  await mobilePage.waitForSelector('.command-center-modal', { state: 'detached' });

  await mobilePage.getByRole('tab', { name: 'Skills' }).click({ force: true });

  const mobileControlContract = await mobilePage.$eval('.skills-tree-map-shell', (shell) => {
    const shellRect = shell.getBoundingClientRect();
    const controls = shell.querySelector('.skills-map-controls');
    if (!controls) return { ok: false, reason: 'missing controls' };
    const controlRect = controls.getBoundingClientRect();
    return {
      ok: true,
      insideShell:
        controlRect.top >= shellRect.top - 1 &&
        controlRect.right <= shellRect.right + 1 &&
        controlRect.bottom <= shellRect.bottom + 1,
    };
  });
  assert.equal(mobileControlContract.ok, true, mobileControlContract.reason ?? 'Missing controls on mobile skills map.');
  assert(mobileControlContract.insideShell, 'Mobile map controls should remain visually inside map shell bounds.');

  const mobileMetricsBeforeZoom = await readMapMetrics(mobilePage);
  await mobilePage.locator('[data-map-control="zoom-in"]').click({ force: true });
  await mobilePage.waitForFunction(
    () => Number.parseFloat(document.querySelector('.skills-tree-map')?.getAttribute('data-map-zoom') ?? '1') > 1.05,
  );
  const mobileMetricsAfterZoom = await readMapMetrics(mobilePage);
  assert(
    mobileMetricsAfterZoom.zoom > mobileMetricsBeforeZoom.zoom + 0.05,
    `Mobile zoom-in should increase map zoom. before=${mobileMetricsBeforeZoom.zoom} after=${mobileMetricsAfterZoom.zoom}`,
  );

  await mobilePage.locator('[data-map-control="fit-reset"]').click({ force: true });
  await mobilePage.waitForFunction(() => {
    const map = document.querySelector('.skills-tree-map');
    if (!map) return false;
    return Number.parseFloat(map.getAttribute('data-map-zoom') ?? '1') < 0.98;
  });

  await mobilePage.locator('[data-map-control="fit-reset"]').click({ force: true });
  await mobilePage.waitForFunction(() => {
    const map = document.querySelector('.skills-tree-map');
    if (!map) return false;
    return Math.abs(Number.parseFloat(map.getAttribute('data-map-zoom') ?? '1') - 1) <= 0.02;
  });

  const mobileInitialScroll = await readMapMetrics(mobilePage);
  await dragMapWithTouch(mobilePage, '.skills-tree-map');
  const mobilePannedScroll = await readMapMetrics(mobilePage);
  assert(
    mobilePannedScroll.left !== mobileInitialScroll.left || mobilePannedScroll.top !== mobileInitialScroll.top,
    `Skill map should pan on touch drag (mobile). Initial=${JSON.stringify(mobileInitialScroll)} next=${JSON.stringify(mobilePannedScroll)}`,
  );
  assert(
    mobilePannedScroll.left >= 0 && mobilePannedScroll.left <= mobilePannedScroll.maxLeft + 0.5,
    `Mobile pan should stay within horizontal bounds. left=${mobilePannedScroll.left} max=${mobilePannedScroll.maxLeft}`,
  );
  assert(
    mobilePannedScroll.top >= 0 && mobilePannedScroll.top <= mobilePannedScroll.maxTop + 0.5,
    `Mobile pan should stay within vertical bounds. top=${mobilePannedScroll.top} max=${mobilePannedScroll.maxTop}`,
  );

  await mobilePage.locator('.skills-card .skill-node').first().click({ force: true });
  await mobilePage.waitForSelector('.skill-modal');
  await mobilePage.keyboard.press('Escape');
  await mobilePage.waitForSelector('.skill-modal', { state: 'detached' });

  await desktopPage.getByRole('tab', { name: 'Operations' }).click({ force: true });

  const timelineStatusText = await desktopPage.$eval('body', (body) => {
    const node = body.querySelector('.timeline-status');
    return node?.textContent?.trim() ?? null;
  });
  if (timelineStatusText && /Current block highlighted below\./i.test(timelineStatusText)) {
    const currentCount = await desktopPage.$$eval('.timeline-item.current', (items) => items.length);
    assert(currentCount > 0, 'Timeline indicates current block is highlighted, but no .timeline-item.current was rendered.');
  }

  console.log('UI regression checks passed');
} finally {
  await desktopPage.close();
  if (mobilePage) await mobilePage.close();
  if (mobileContext) await mobileContext.close();
  await browser.close();
}
