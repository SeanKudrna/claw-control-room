import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const APP_URL = process.env.UI_TEST_URL || 'http://127.0.0.1:4173/claw-control-room/';

function mockStatusPayload() {
  const nowMs = Date.now();
  return {
    generatedAt: new Date(nowMs).toISOString(),
    generatedAtLocal: '2026-02-19 01:15 CST',
    controlRoomVersion: '1.4.38',
    currentFocus: 'Skill action flow verification',
    activeWork: 'Issue #50 skills actions',
    reliability: { status: 'green' },
    timeline: [],
    nextJobs: [],
    findings: [],
    workstream: {
      now: ['Validate learning actions'],
      next: [],
      done: [],
    },
    charts: {
      jobSuccessTrend: [],
      reliabilityTrend: [],
    },
    activity: [],
    skills: {
      activeCount: 1,
      plannedCount: 0,
      lockedCount: 1,
      nodes: [
        {
          id: 'runtime-orchestration',
          name: 'Runtime Orchestration',
          description: 'Root skill domain.',
          effect: 'Coordinates runtime lanes.',
          state: 'active',
          tier: 1,
          currentTier: 4,
          maxTier: 5,
          nextTier: 5,
          nextUnlock: 'Tier 5 unlocks stewardship patterns.',
          dependencies: [],
          learnedAt: '2026-02-18',
          level: 4,
          progress: 0.8,
        },
        {
          id: 'reliability-guardrails',
          name: 'Reliability Guardrails',
          description: 'Locked target skill for action flow tests.',
          effect: 'Improves degraded-mode trust cues.',
          state: 'locked',
          tier: 2,
          currentTier: 0,
          maxTier: 5,
          nextTier: 1,
          nextUnlock: 'Tier 1 unlocks baseline guardrail execution.',
          dependencies: ['runtime-orchestration'],
          learnedAt: null,
          level: 0,
          progress: 0,
        },
      ],
      evolution: {
        sourceArtifacts: [],
        deterministicSeed: 'skill-action-flow-seed',
        lastProcessedAt: new Date(nowMs).toISOString(),
        mode: 'mock-v1',
      },
    },
    runtime: {
      status: 'idle',
      isIdle: true,
      activeCount: 0,
      activeRuns: [],
      checkedAtMs: nowMs,
      source: 'live-reconciler',
      revision: 'rtv1-00010001',
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
  await page.getByRole('tab', { name: 'Skills' }).click({ force: true });

  const lockedNode = page.locator('.skill-node[data-node-id="reliability-guardrails"]');
  await lockedNode.click({ force: true });
  await page.waitForSelector('.skill-modal');

  const startLearningButton = page.locator('[data-skill-action="start-learning"]');
  await startLearningButton.waitFor();
  assert.equal(await startLearningButton.isEnabled(), true, 'Start Learning should be enabled for dependency-met locked node.');

  await startLearningButton.click({ force: true });

  await page.waitForFunction(() => {
    const marker = document.querySelector('[data-selected-job-state]');
    return marker?.getAttribute('data-selected-job-state') === 'pending';
  });

  await page.waitForFunction(() => {
    const marker = document.querySelector('[data-selected-job-state]');
    return marker?.getAttribute('data-selected-job-state') === 'running';
  }, { timeout: 10_000 });

  await page.waitForFunction(() => {
    const marker = document.querySelector('[data-selected-job-state]');
    return marker?.getAttribute('data-selected-job-state') === 'completed';
  }, { timeout: 14_000 });

  const progressedNodeContract = await page.$eval('.skill-node[data-node-id="reliability-guardrails"]', (node) => {
    return {
      progress: node.querySelector('.skill-node-progress')?.textContent?.trim() ?? '',
      modalState: document.querySelector('.skill-modal-state-pill')?.textContent?.trim() ?? '',
      jobState: node.getAttribute('data-skill-job-state') ?? 'none',
    };
  });

  assert.equal(progressedNodeContract.jobState, 'completed', 'Node should expose completed job state after learning run.');
  assert.equal(progressedNodeContract.progress, 'Tier 1/5', 'Completed learning run should deterministically promote locked skill to Tier 1/5.');
  assert.notEqual(progressedNodeContract.modalState, 'Locked', 'Skill should no longer render as locked after completion.');

  const discoverButton = page.locator('[data-skill-action="discover-new-skill"]');
  await discoverButton.click({ force: true });

  const discoveryInput = page.locator('#skill-discovery-name');
  await discoveryInput.fill('Chaos Engineering');
  await page.locator('[data-skill-action="create-candidate"]').click({ force: true });

  const candidateNode = page.locator('.skill-node[data-node-id="candidate-chaos-engineering"]');
  await candidateNode.waitFor({ state: 'visible' });

  const candidateContract = await page.$eval('.skill-node[data-node-id="candidate-chaos-engineering"]', (node) => ({
    statePill: node.querySelector('.skill-node-state')?.textContent?.trim() ?? '',
    tierLabel: node.querySelector('.skill-node-progress')?.textContent?.trim() ?? '',
  }));

  assert.equal(candidateContract.statePill, 'Locked', 'Discover flow should create candidate nodes in locked state.');
  assert.equal(candidateContract.tierLabel, 'Tier 0/5', 'Candidate nodes should start at deterministic Tier 0/5 baseline.');

  console.log('Skill action -> job -> state transition checks passed');
} finally {
  await page.close();
  await browser.close();
}
