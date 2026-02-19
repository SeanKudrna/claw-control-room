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
        deterministicSeed: 'runtime-modal-shot',
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

  await page.locator('.runtime-detail-btn').nth(0).click({ force: true });
  await page.waitForSelector('.runtime-modal');
  await page.screenshot({
    path: 'status/ui-validation/issue50-job-details-model-thinking-desktop-baseline.png',
    fullPage: true,
  });

  await page.click('.runtime-modal-close');
  await page.waitForSelector('.runtime-modal', { state: 'detached' });

  await page.locator('.runtime-detail-btn').nth(1).click({ force: true });
  await page.waitForSelector('.runtime-modal');
  await page.screenshot({
    path: 'status/ui-validation/issue50-job-details-model-thinking-desktop-fallback.png',
    fullPage: true,
  });
} finally {
  await page.close();
  await browser.close();
}
