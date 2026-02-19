import type { SkillNode } from '../types/status';

export interface SkillTreePosition {
  x: number;
  y: number;
  angle: number;
  ringIndex: number;
  /** Dependency depth from the closest root hub. */
  depth: number;
  /** Root hub id this node is anchored to. */
  rootId: string;
  /** First branch id under the root hub. */
  branchId: string;
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

interface PlacementMeta {
  depth: number;
  rootId: string;
  branchId: string;
  parentId: string | null;
}

interface BranchBand {
  center: number;
  min: number;
  max: number;
}

const TAU = Math.PI * 2;
const HUB_RING_RADIUS = 140;
const DEPTH_RING_STEP = 236;
const NODE_SAFE_DIAMETER = 196;
const CANVAS_EDGE_PADDING = 270;

function compareSkillNodes(a: SkillNode, b: SkillNode): number {
  return a.tier - b.tier || a.name.localeCompare(b.name) || a.id.localeCompare(b.id);
}

function normalizeAngle(angle: number): number {
  let value = angle % TAU;
  if (value < 0) value += TAU;
  return value;
}

function dedupe<T>(values: T[]): T[] {
  const seen = new Set<T>();
  const result: T[] = [];
  for (const value of values) {
    if (seen.has(value)) continue;
    seen.add(value);
    result.push(value);
  }
  return result;
}

function spreadAnglesInBand(baseAngles: number[], minSeparation: number, minAngle: number, maxAngle: number): number[] {
  if (!baseAngles.length) return [];
  if (baseAngles.length === 1) return [Math.max(minAngle, Math.min(maxAngle, baseAngles[0]))];

  const span = Math.max(0.001, maxAngle - minAngle);
  const effectiveSeparation = Math.min(minSeparation, span / Math.max(1, baseAngles.length - 1));

  const sorted = baseAngles
    .map((angle, index) => ({
      index,
      angle: Math.max(minAngle, Math.min(maxAngle, angle)),
    }))
    .sort((a, b) => a.angle - b.angle || a.index - b.index);

  for (let pass = 0; pass < 6; pass += 1) {
    for (let i = 0; i < sorted.length - 1; i += 1) {
      const current = sorted[i];
      const next = sorted[i + 1];
      const gap = next.angle - current.angle;
      if (gap >= effectiveSeparation) continue;
      const shift = (effectiveSeparation - gap) / 2;
      current.angle -= shift;
      next.angle += shift;
    }

    if (sorted[0].angle < minAngle) {
      const delta = minAngle - sorted[0].angle;
      for (const entry of sorted) entry.angle += delta;
    }

    const last = sorted[sorted.length - 1];
    if (last.angle > maxAngle) {
      const delta = last.angle - maxAngle;
      for (const entry of sorted) entry.angle -= delta;
    }
  }

  const result = new Array(baseAngles.length).fill(0);
  for (const entry of sorted) {
    result[entry.index] = Math.max(minAngle, Math.min(maxAngle, entry.angle));
  }
  return result;
}

/**
 * Deterministic dependency-aware layout model.
 *
 * Rules:
 * 1) Sort nodes by (tier, name, id) for stable ordering.
 * 2) Build root hubs from dependency-free nodes; every node inherits a stable primary parent.
 * 3) Assign each root one angular sector and each first-hop branch a deterministic sub-band.
 * 4) Place depth rings using fixed radii (`HUB_RING_RADIUS` + depth * `DEPTH_RING_STEP`).
 * 5) Children are parent-guided within branch bands, then angle-separated to avoid overlap.
 *
 * This keeps the map refresh-stable (no jitter) while preserving meaningful hub/branch structure.
 */
export function computeSkillTreeLayout(nodes: SkillNode[], width: number, height: number): SkillTreeLayout {
  const orderedNodes = nodes.slice().sort(compareSkillNodes);
  const nodeById = new Map(orderedNodes.map((node) => [node.id, node]));

  if (!orderedNodes.length) {
    const fallbackWidth = Math.max(1200, width);
    const fallbackHeight = Math.max(900, height);
    return {
      width: fallbackWidth,
      height: fallbackHeight,
      centerX: fallbackWidth / 2,
      centerY: fallbackHeight / 2,
      positions: new Map(),
      edges: [],
    };
  }

  const compareNodeIds = (aId: string, bId: string): number => {
    const a = nodeById.get(aId);
    const b = nodeById.get(bId);
    if (!a || !b) return aId.localeCompare(bId);
    return compareSkillNodes(a, b);
  };

  const dependencyMap = new Map<string, string[]>();
  for (const node of orderedNodes) {
    const deps = dedupe(node.dependencies.filter((depId) => depId !== node.id && nodeById.has(depId))).sort(compareNodeIds);
    dependencyMap.set(node.id, deps);
  }

  const explicitRoots = orderedNodes
    .filter((node) => (dependencyMap.get(node.id) ?? []).length === 0)
    .map((node) => node.id);

  const rootIds = explicitRoots.length ? explicitRoots : [orderedNodes[0].id];
  const rootSet = new Set(rootIds);
  const placementMetaById = new Map<string, PlacementMeta>();

  const resolveMeta = (nodeId: string, stack: Set<string> = new Set()): PlacementMeta => {
    const cached = placementMetaById.get(nodeId);
    if (cached) return cached;

    if (stack.has(nodeId)) {
      const fallback: PlacementMeta = {
        depth: 1,
        rootId: rootIds[0],
        branchId: nodeId,
        parentId: null,
      };
      placementMetaById.set(nodeId, fallback);
      return fallback;
    }

    stack.add(nodeId);

    const deps = dependencyMap.get(nodeId) ?? [];
    let resolved: PlacementMeta;

    if (!deps.length || rootSet.has(nodeId)) {
      resolved = {
        depth: rootSet.has(nodeId) ? 0 : 1,
        rootId: rootSet.has(nodeId) ? nodeId : rootIds[0],
        branchId: nodeId,
        parentId: null,
      };
    } else {
      const parentId = deps[0];
      const parentMeta = resolveMeta(parentId, stack);
      resolved = {
        depth: parentMeta.depth + 1,
        rootId: parentMeta.rootId,
        branchId: parentMeta.depth === 0 ? nodeId : parentMeta.branchId,
        parentId,
      };
    }

    stack.delete(nodeId);
    placementMetaById.set(nodeId, resolved);
    return resolved;
  };

  for (const node of orderedNodes) {
    resolveMeta(node.id);
  }

  const maxDepth = Math.max(...orderedNodes.map((node) => placementMetaById.get(node.id)?.depth ?? 0));
  const requiredRadius = HUB_RING_RADIUS + maxDepth * DEPTH_RING_STEP + NODE_SAFE_DIAMETER;

  const safeWidth = Math.max(width, requiredRadius * 2 + CANVAS_EDGE_PADDING * 2);
  const safeHeight = Math.max(height, requiredRadius * 2 + CANVAS_EDGE_PADDING * 2);
  const centerX = safeWidth / 2;
  const centerY = safeHeight / 2;

  const rootAngles = new Map<string, number>();
  const rootStep = TAU / Math.max(1, rootIds.length);
  rootIds.forEach((rootId, index) => {
    rootAngles.set(rootId, -Math.PI / 2 + rootStep * index);
  });

  const branchesByRoot = new Map<string, string[]>();
  for (const rootId of rootIds) {
    const branchIds = dedupe(
      orderedNodes
        .filter((node) => placementMetaById.get(node.id)?.rootId === rootId)
        .map((node) => placementMetaById.get(node.id)?.branchId ?? node.id),
    ).sort(compareNodeIds);

    branchesByRoot.set(rootId, branchIds.length ? branchIds : [rootId]);
  }

  const branchBands = new Map<string, BranchBand>();
  for (const rootId of rootIds) {
    const rootAngle = rootAngles.get(rootId) ?? -Math.PI / 2;
    const rootCount = Math.max(1, rootIds.length);
    const rootSpan = rootCount === 1
      ? TAU - 0.65
      : Math.max(1.35, (TAU / rootCount) * 0.88);

    const branches = branchesByRoot.get(rootId) ?? [rootId];
    const branchCenters = branches.map((_, index) => {
      if (branches.length === 1) return rootAngle;
      const step = rootSpan / Math.max(1, branches.length - 1);
      return rootAngle - rootSpan / 2 + index * step;
    });

    for (let index = 0; index < branches.length; index += 1) {
      const branchId = branches[index];
      const center = branchCenters[index] ?? rootAngle;
      const left = index === 0
        ? rootAngle - rootSpan / 2
        : ((branchCenters[index - 1] ?? center) + center) / 2;
      const right = index === branches.length - 1
        ? rootAngle + rootSpan / 2
        : (center + (branchCenters[index + 1] ?? center)) / 2;
      const gutter = Math.min(0.1, Math.max(0.03, (right - left) * 0.12));
      branchBands.set(branchId, {
        center,
        min: left + gutter,
        max: right - gutter,
      });
    }

  }

  const positions = new Map<string, SkillTreePosition>();
  const rawAnglesById = new Map<string, number>();

  // Depth 0 hubs
  const rootRingRadius = rootIds.length === 1 ? 0 : HUB_RING_RADIUS * 0.72;
  for (const rootId of rootIds) {
    const rootAngle = rootAngles.get(rootId) ?? -Math.PI / 2;
    const x = centerX + Math.cos(rootAngle) * rootRingRadius;
    const y = centerY + Math.sin(rootAngle) * rootRingRadius;
    const meta = placementMetaById.get(rootId) ?? {
      depth: 0,
      rootId,
      branchId: rootId,
      parentId: null,
    };

    positions.set(rootId, {
      x,
      y,
      angle: normalizeAngle(rootAngle),
      ringIndex: 0,
      depth: 0,
      rootId: meta.rootId,
      branchId: meta.branchId,
    });
    rawAnglesById.set(rootId, rootAngle);
  }

  for (let depth = 1; depth <= maxDepth; depth += 1) {
    const radius = HUB_RING_RADIUS + depth * DEPTH_RING_STEP;

    for (const rootId of rootIds) {
      const branchIds = branchesByRoot.get(rootId) ?? [rootId];

      for (const branchId of branchIds) {
        const nodesForDepth = orderedNodes
          .filter((node) => {
            const meta = placementMetaById.get(node.id);
            return meta?.depth === depth && meta.rootId === rootId && meta.branchId === branchId;
          })
          .sort((a, b) => {
            const metaA = placementMetaById.get(a.id);
            const metaB = placementMetaById.get(b.id);
            const parentA = metaA?.parentId ?? '';
            const parentB = metaB?.parentId ?? '';
            return compareNodeIds(parentA, parentB) || compareSkillNodes(a, b);
          });

        if (!nodesForDepth.length) continue;

        const branchBand = branchBands.get(branchId) ?? {
          center: rootAngles.get(rootId) ?? -Math.PI / 2,
          min: (rootAngles.get(rootId) ?? -Math.PI / 2) - 0.55,
          max: (rootAngles.get(rootId) ?? -Math.PI / 2) + 0.55,
        };

        const nodeIds: string[] = [];
        const desiredAngles: number[] = [];

        const childrenByParent = new Map<string, SkillNode[]>();
        for (const node of nodesForDepth) {
          const parentId = placementMetaById.get(node.id)?.parentId ?? `__root__${branchId}`;
          const existing = childrenByParent.get(parentId) ?? [];
          existing.push(node);
          childrenByParent.set(parentId, existing);
        }

        const parentOrder = [...childrenByParent.keys()].sort((a, b) => {
          const angleA = rawAnglesById.get(a) ?? branchBand.center;
          const angleB = rawAnglesById.get(b) ?? branchBand.center;
          return angleA - angleB || compareNodeIds(a, b);
        });

        for (const parentId of parentOrder) {
          const siblings = (childrenByParent.get(parentId) ?? []).sort(compareSkillNodes);
          const parentAngle = rawAnglesById.get(parentId) ?? branchBand.center;
          const baseAngle = depth === 1
            ? branchBand.center
            : parentAngle * 0.72 + branchBand.center * 0.28;
          const siblingStep = Math.min(0.42, Math.max(0.18, 0.28 + depth * 0.01));

          siblings.forEach((node, siblingIndex) => {
            const offset = (siblingIndex - (siblings.length - 1) / 2) * siblingStep;
            nodeIds.push(node.id);
            desiredAngles.push(baseAngle + offset);
          });
        }

        const minSeparation = Math.min(0.95, Math.max(0.24, (NODE_SAFE_DIAMETER + 22) / Math.max(radius, 1)));
        const resolvedAngles = spreadAnglesInBand(desiredAngles, minSeparation, branchBand.min, branchBand.max);

        nodeIds.forEach((nodeId, index) => {
          const angle = resolvedAngles[index] ?? branchBand.center;
          const meta = placementMetaById.get(nodeId) ?? {
            depth,
            rootId,
            branchId,
            parentId: null,
          };

          positions.set(nodeId, {
            x: centerX + Math.cos(angle) * radius,
            y: centerY + Math.sin(angle) * radius,
            angle: normalizeAngle(angle),
            ringIndex: depth,
            depth,
            rootId: meta.rootId,
            branchId: meta.branchId,
          });
          rawAnglesById.set(nodeId, angle);
        });
      }
    }
  }

  const edges: SkillTreeEdge[] = [];
  for (const node of orderedNodes) {
    for (const dependencyId of dependencyMap.get(node.id) ?? []) {
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
