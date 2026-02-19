import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const APP_URL = process.env.UI_TEST_URL || 'http://127.0.0.1:4173/claw-control-room/';

function mockStatusPayload() {
  const nowMs = Date.now();
  return {
    generatedAt: new Date(nowMs).toISOString(),
    generatedAtLocal: '2026-02-19 00:40 CST',
    controlRoomVersion: '1.4.37',
    currentFocus: 'Runtime transparency verification',
    activeWork: 'Overnight sprint',
    reliability: { status: 'green' },
    timeline: [],
    nextJobs: [],
    findings: [],
    workstream: {
      now: ['Validate runtime modal metadata'],
      next: [],
      done: [],
    },
    charts: {
      jobSuccessTrend: [],
      reliabilityTrend: [],
    },
    activity: [],
    skills: {
      activeCount: 0,
      plannedCount: 0,
      lockedCount: 0,
      nodes: [],
      evolution: {
        sourceArtifacts: [],
        deterministicSeed: 'runtime-modal-mock',
        lastProcessedAt: new Date(nowMs).toISOString(),
        mode: 'mock-v1',
      },
    },
    runtime: {
      status: 'running',
      isIdle: false,
      activeCount: 2,
      activeRuns: [
        {
          jobId: 'job-baseline',
          jobName: 'Baseline Job',
          sessionId: 'session-baseline',
          sessionKey: 'agent:main:cron:job-baseline:run:session-baseline',
          startedAtMs: nowMs - 30_000,
          startedAtLocal: '2026-02-19 00:39:30',
          runningForMs: 30_000,
          summary: 'Baseline runtime metadata row',
          activityType: 'cron',
          model: 'openai-codex/gpt-5.3-codex',
          thinking: 'high',
        },
        {
          jobId: 'job-missing',
          jobName: 'Missing Metadata Job',
          sessionId: 'session-missing',
          sessionKey: 'agent:main:cron:job-missing:run:session-missing',
          startedAtMs: nowMs - 18_000,
          startedAtLocal: '2026-02-19 00:39:42',
          runningForMs: 18_000,
          summary: 'Row without model/thinking metadata',
          activityType: 'cron',
        },
      ],
      checkedAtMs: nowMs,
      source: 'live-reconciler',
      revision: 'rtv1-00010000',
      snapshotMode: 'live',
      degradedReason: '',
    },
  };
}

async function runtimeDetailMap(page) {
  return page.$$eval('.runtime-detail-grid > div', (cards) => {
    const out = {};
    for (const card of cards) {
      const label = card.querySelector('dt')?.textContent?.trim();
      const value = card.querySelector('dd')?.textContent?.trim() ?? '';
      if (label) out[label] = value;
    }
    return out;
  });
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1512, height: 982 } });

try {
  const payload = mockStatusPayload();

  await page.route('**/claw-control-room/data/source.json*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ url: '' }),
    });
  });

  await page.route('**/claw-control-room/data/status.json*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(payload),
    });
  });

  await page.goto(APP_URL, { waitUntil: 'networkidle' });
  await page.waitForSelector('.runtime-list .runtime-item');

  const detailButtons = page.locator('.runtime-detail-btn');
  assert.equal(await detailButtons.count(), 2, 'Runtime list should render two details buttons for mock rows.');

  await detailButtons.nth(0).click({ force: true });
  await page.waitForSelector('.runtime-modal');

  const firstDetails = await runtimeDetailMap(page);
  assert.equal(firstDetails['Model used'], 'openai-codex/gpt-5.3-codex', 'Modal should show explicit model metadata.');
  assert.equal(firstDetails['Thinking level'], 'High', 'Modal should show normalized thinking label.');
  assert(
    firstDetails['Baseline target']?.includes('Baseline match'),
    `Baseline row should show a positive baseline indicator. Got: ${firstDetails['Baseline target']}`,
  );

  await page.click('.runtime-modal-close');
  await page.waitForSelector('.runtime-modal', { state: 'detached' });

  await detailButtons.nth(1).click({ force: true });
  await page.waitForSelector('.runtime-modal');

  const secondDetails = await runtimeDetailMap(page);
  assert.equal(secondDetails['Model used'], 'Not reported', 'Modal should show model fallback when metadata is missing.');
  assert.equal(secondDetails['Thinking level'], 'Not reported', 'Modal should show thinking fallback when metadata is missing.');
  assert(
    secondDetails['Baseline target']?.includes('unavailable'),
    `Missing metadata row should show unavailable baseline check text. Got: ${secondDetails['Baseline target']}`,
  );

  console.log('Runtime job details modal checks passed');
} finally {
  await page.close();
  await browser.close();
}
