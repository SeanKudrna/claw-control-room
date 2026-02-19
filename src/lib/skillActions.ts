import type { SkillNode, SkillState } from '../types/status';
import { getSkillTierLadder, getSkillTierProgress } from './skillsModel';

export type SkillLearningJobState = 'pending' | 'running' | 'completed';

export interface SkillLearningJob {
  id: string;
  type: 'learning';
  skillId: string;
  createdAtMs: number;
  startedAtMs: number | null;
  completedAtMs: number | null;
  attempt: number;
  queueDelayMs: number;
  runDurationMs: number;
  state: SkillLearningJobState;
}

const LEARNING_QUEUE_DELAY_MS = 900;
const LEARNING_DURATION_BASE_MS = 3_200;
const LEARNING_DURATION_SPREAD_MS = 2_100;
const CANDIDATE_PREFIX = 'candidate';

function hashText(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
}

export function deterministicLearningDurationMs(skillId: string, attempt: number): number {
  const seed = hashText(`${skillId}:${attempt}`);
  return LEARNING_DURATION_BASE_MS + (seed % LEARNING_DURATION_SPREAD_MS);
}

export function createLearningJob(skillId: string, attempt: number, nowMs: number): SkillLearningJob {
  return {
    id: `learn:${skillId}:${attempt}`,
    type: 'learning',
    skillId,
    createdAtMs: nowMs,
    startedAtMs: null,
    completedAtMs: null,
    attempt,
    queueDelayMs: LEARNING_QUEUE_DELAY_MS,
    runDurationMs: deterministicLearningDurationMs(skillId, attempt),
    state: 'pending',
  };
}

export function transitionLearningJobs(jobs: SkillLearningJob[], nowMs: number): SkillLearningJob[] {
  return jobs.map((job) => {
    if (job.state === 'completed') return job;

    if (job.state === 'pending') {
      if (nowMs < job.createdAtMs + job.queueDelayMs) return job;
      return {
        ...job,
        state: 'running',
        startedAtMs: job.createdAtMs + job.queueDelayMs,
      };
    }

    const startedAtMs = job.startedAtMs ?? (job.createdAtMs + job.queueDelayMs);
    const completedAtMs = startedAtMs + job.runDurationMs;
    if (nowMs < completedAtMs) {
      if (startedAtMs === job.startedAtMs) return job;
      return {
        ...job,
        startedAtMs,
      };
    }

    return {
      ...job,
      state: 'completed',
      startedAtMs,
      completedAtMs,
    };
  });
}

export function latestLearningJobBySkill(jobs: SkillLearningJob[]): Map<string, SkillLearningJob> {
  const latest = new Map<string, SkillLearningJob>();
  for (const job of jobs) {
    const existing = latest.get(job.skillId);
    if (!existing || existing.createdAtMs <= job.createdAtMs) {
      latest.set(job.skillId, job);
    }
  }
  return latest;
}

export function isDependencyUnlocked(node: SkillNode | undefined): boolean {
  if (!node) return false;
  const tier = getSkillTierProgress(node);
  return tier.currentTier > 0 || node.state === 'active';
}

export function areSkillDependenciesMet(node: SkillNode, nodeById: Map<string, SkillNode>): boolean {
  return node.dependencies.every((depId) => isDependencyUnlocked(nodeById.get(depId)));
}

function tierState(currentTier: number): SkillState {
  if (currentTier <= 0) return 'locked';
  if (currentTier >= 3) return 'active';
  return 'planned';
}

export function applyLearningCompletion(node: SkillNode, completedAtMs: number): SkillNode {
  const progress = getSkillTierProgress(node);
  const nextTierValue = Math.min(progress.maxTier, progress.currentTier + 1);
  const nextTier = nextTierValue < progress.maxTier ? nextTierValue + 1 : null;
  const ladder = getSkillTierLadder({ ...node, currentTier: nextTierValue });
  const nextUnlock =
    nextTier !== null
      ? (ladder.find((entry) => entry.tier === nextTier)?.difference ??
        `Tier ${nextTier} expands execution capability in this domain.`)
      : null;

  const completedDate = new Date(completedAtMs).toISOString().slice(0, 10);

  return {
    ...node,
    currentTier: nextTierValue,
    level: nextTierValue,
    state: tierState(nextTierValue),
    progress: Number((nextTierValue / progress.maxTier).toFixed(2)),
    nextTier,
    nextUnlock,
    learnedAt: node.learnedAt ?? completedDate,
  };
}

function slugify(value: string): string {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)+/g, '');
  return slug || 'new-skill';
}

export function createCandidateSkillNode(
  name: string,
  sourceNode: SkillNode,
  existingNodes: SkillNode[],
): SkillNode {
  const slug = slugify(name);
  const existingIds = new Set(existingNodes.map((node) => node.id));
  let candidateId = `${CANDIDATE_PREFIX}-${slug}`;
  let suffix = 2;
  while (existingIds.has(candidateId)) {
    candidateId = `${CANDIDATE_PREFIX}-${slug}-${suffix}`;
    suffix += 1;
  }

  const highestTier = existingNodes.reduce((max, node) => Math.max(max, node.tier), 0);

  return {
    id: candidateId,
    name: name.trim(),
    description: `Candidate skill discovered from ${sourceNode.name}. Validate fit and prerequisites, then start learning to unlock Tier 1.`,
    effect: `Potential unlock path branching from ${sourceNode.name}.`,
    state: 'locked',
    tier: highestTier + 1,
    currentTier: 0,
    maxTier: 5,
    nextTier: 1,
    nextUnlock: 'Unlock Tier 1 by running Start Learning once prerequisites are met.',
    dependencies: [sourceNode.id],
    learnedAt: null,
    level: 0,
    progress: 0,
  };
}
