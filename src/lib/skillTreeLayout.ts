import type { SkillNode } from '../types/status';

export interface SkillTreePosition {
  x: number;
  y: number;
  angle: number;
  ringIndex: number;
}

export interface SkillTreeEdge {
  key: string;
  fromId: string;
  toId: string;
  state: 'locked' | 'unlocked';
}

export interface SkillTreeLayout {
  width: number;
  height: number;
  centerX: number;
  centerY: number;
  positions: Map<string, SkillTreePosition>;
  edges: SkillTreeEdge[];
}

const TAU = Math.PI * 2;

function normalizeAngle(angle: number): number {
  let value = angle % TAU;
  if (value < 0) value += TAU;
  return value;
}

function averageAngle(values: number[]): number {
  if (!values.length) return 0;
  const x = values.reduce((sum, angle) => sum + Math.cos(angle), 0);
  const y = values.reduce((sum, angle) => sum + Math.sin(angle), 0);
  return normalizeAngle(Math.atan2(y, x));
}

function spreadAngles(baseAngles: number[], minSeparation: number): number[] {
  if (baseAngles.length < 2) return baseAngles;

  const sorted = baseAngles
    .map((angle, index) => ({ angle: normalizeAngle(angle), index }))
    .sort((a, b) => a.angle - b.angle);

  for (let pass = 0; pass < 5; pass += 1) {
    for (let i = 0; i < sorted.length; i += 1) {
      const current = sorted[i];
      const next = sorted[(i + 1) % sorted.length];
      const nextAngle = i + 1 < sorted.length ? next.angle : next.angle + TAU;
      const gap = nextAngle - current.angle;
      if (gap < minSeparation) {
        const shift = (minSeparation - gap) / 2;
        current.angle = normalizeAngle(current.angle - shift);
        next.angle = normalizeAngle(next.angle + shift);
      }
    }
    sorted.sort((a, b) => a.angle - b.angle);
  }

  const result = new Array(baseAngles.length).fill(0);
  for (const item of sorted) {
    result[item.index] = item.angle;
  }
  return result;
}

export function computeSkillTreeLayout(nodes: SkillNode[], width: number, height: number): SkillTreeLayout {
  const safeWidth = Math.max(1700, width);
  const safeHeight = Math.max(1400, height);
  const centerX = safeWidth / 2;
  const centerY = safeHeight / 2;

  const tiers = [...new Set(nodes.map((node) => node.tier))].sort((a, b) => a - b);
  const ringStep = 170;

  const positions = new Map<string, SkillTreePosition>();

  for (let tierIndex = 0; tierIndex < tiers.length; tierIndex += 1) {
    const tier = tiers[tierIndex];
    const tierNodes = nodes
      .filter((node) => node.tier === tier)
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name));

    if (!tierNodes.length) continue;

    const defaultStep = TAU / tierNodes.length;
    const defaultOffset = tierIndex % 2 === 0 ? -Math.PI / 2 : -Math.PI / 2 + defaultStep / 2;

    const desiredAngles = tierNodes.map((node, index) => {
      if (tierNodes.length === 1) {
        return normalizeAngle(-Math.PI / 2 + tierIndex * 0.88);
      }

      const depAngles = node.dependencies
        .map((depId) => positions.get(depId)?.angle)
        .filter((angle): angle is number => typeof angle === 'number');
      if (depAngles.length) {
        const inherited = averageAngle(depAngles);
        const drift = (index - (tierNodes.length - 1) / 2) * 0.34 + tierIndex * 0.17;
        return normalizeAngle(inherited + drift);
      }
      return normalizeAngle(defaultOffset + index * defaultStep);
    });

    const minSeparation = Math.min(1.1, Math.max(0.36, defaultStep * 0.72));
    const resolvedAngles = spreadAngles(desiredAngles, minSeparation);
    const radius = tierIndex * ringStep;

    tierNodes.forEach((node, index) => {
      const angle = resolvedAngles[index];
      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;

      positions.set(node.id, {
        x: Math.min(safeWidth - 84, Math.max(84, x)),
        y: Math.min(safeHeight - 84, Math.max(84, y)),
        angle,
        ringIndex: tierIndex,
      });
    });
  }

  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const edges: SkillTreeEdge[] = [];

  for (const node of nodes) {
    for (const dependencyId of node.dependencies) {
      if (!positions.has(dependencyId) || !positions.has(node.id)) continue;
      const dependency = nodeById.get(dependencyId);
      const unlocked = dependency && dependency.state !== 'locked';
      edges.push({
        key: `${dependencyId}->${node.id}`,
        fromId: dependencyId,
        toId: node.id,
        state: unlocked ? 'unlocked' : 'locked',
      });
    }
  }

  return {
    width: safeWidth,
    height: safeHeight,
    centerX,
    centerY,
    positions,
    edges,
  };
}
