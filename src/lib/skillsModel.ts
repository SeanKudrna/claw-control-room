import type { SkillNode, SkillTierDefinition } from '../types/status';

const FALLBACK_MAX_TIER = 5;

const DEFAULT_LADDER_COPY: Array<Pick<SkillTierDefinition, 'tier' | 'title' | 'definition' | 'difference'>> = [
  {
    tier: 1,
    title: 'Foundation',
    definition: 'Build baseline familiarity, vocabulary, and repeatable starter routines.',
    difference: 'Unlocks dependable baseline execution for this domain.',
  },
  {
    tier: 2,
    title: 'Guided Delivery',
    definition: 'Ship scoped improvements with lightweight guidance and QA feedback loops.',
    difference: 'Moves from understanding to repeatable hands-on delivery.',
  },
  {
    tier: 3,
    title: 'Independent Reliability',
    definition: 'Run end-to-end workflows confidently with consistent outcome quality.',
    difference: 'Graduates from guided execution to autonomous ownership.',
  },
  {
    tier: 4,
    title: 'Strategic Optimization',
    definition: 'Improve systems proactively through instrumentation, guardrails, and workflow design.',
    difference: 'Shifts from delivery to durable system-level optimization.',
  },
  {
    tier: 5,
    title: 'System Stewardship',
    definition: 'Set standards, coach pattern reuse, and evolve long-term domain capability.',
    difference: 'Represents expert stewardship and continuous compounding impact.',
  },
];

function clampTier(value: number, maxTier: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(maxTier, Math.trunc(value)));
}

function inferCurrentTier(node: SkillNode, maxTier: number): number {
  if (typeof node.currentTier === 'number') {
    return clampTier(node.currentTier, maxTier);
  }

  if (typeof node.level === 'number' && node.level > 0) {
    return clampTier(node.level, maxTier);
  }

  const progress = Number.isFinite(node.progress) ? Math.max(0, Math.min(1, node.progress)) : 0;
  const inferred = Math.floor(progress * maxTier + 1e-6);
  if (progress > 0 && inferred === 0) return 1;
  return clampTier(inferred, maxTier);
}

export interface SkillTierProgress {
  currentTier: number;
  maxTier: number;
  nextTier: number | null;
  completedCount: number;
}

export function getSkillTierProgress(node: SkillNode): SkillTierProgress {
  const maxTierRaw = typeof node.maxTier === 'number' ? node.maxTier : FALLBACK_MAX_TIER;
  const maxTier = Math.max(1, Math.trunc(maxTierRaw));
  const currentTier = inferCurrentTier(node, maxTier);

  const nextTier =
    typeof node.nextTier === 'number'
      ? clampTier(node.nextTier, maxTier) || null
      : currentTier < maxTier
        ? currentTier + 1
        : null;

  return {
    currentTier,
    maxTier,
    nextTier,
    completedCount: currentTier,
  };
}

function isTierDefinition(value: unknown): value is SkillTierDefinition {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.tier === 'number' &&
    typeof candidate.title === 'string' &&
    typeof candidate.definition === 'string' &&
    typeof candidate.difference === 'string'
  );
}

export function getSkillTierLadder(node: SkillNode): SkillTierDefinition[] {
  const progress = getSkillTierProgress(node);

  if (Array.isArray(node.tierLadder) && node.tierLadder.every((entry) => isTierDefinition(entry))) {
    const normalized = node.tierLadder
      .slice()
      .sort((a, b) => a.tier - b.tier)
      .filter((entry) => entry.tier >= 1 && entry.tier <= progress.maxTier);
    if (normalized.length) return normalized;
  }

  return DEFAULT_LADDER_COPY.map((tier) => ({
    ...tier,
    tier: Math.min(progress.maxTier, tier.tier),
    definition: `${node.name}: ${tier.definition}`,
  })).filter((tier, index, all) => tier.tier >= 1 && tier.tier <= progress.maxTier && all.findIndex((item) => item.tier === tier.tier) === index);
}
