import { useMemo, useState } from 'react';
import type { SkillNode, SkillsPayload } from '../types/status';

interface SkillsTreeProps {
  skills: SkillsPayload;
}

type VisualState = 'active' | 'in-progress' | 'planned' | 'locked';

function stateLabel(state: VisualState): string {
  if (state === 'active') return 'Active';
  if (state === 'in-progress') return 'In Progress';
  if (state === 'planned') return 'Planned';
  return 'Locked';
}

function toVisualState(node: SkillNode): VisualState {
  if (node.state === 'locked') return 'locked';
  if (node.state === 'active' || node.progress >= 1) return 'active';
  if (node.progress > 0) return 'in-progress';
  return 'planned';
}

export function SkillsTree({ skills }: SkillsTreeProps) {
  const [selectedId, setSelectedId] = useState<string>(skills.nodes[0]?.id ?? '');

  const selected = useMemo(
    () => skills.nodes.find((node) => node.id === selectedId) ?? skills.nodes[0] ?? null,
    [skills.nodes, selectedId],
  );

  const nodeNameById = useMemo(
    () => new Map(skills.nodes.map((node) => [node.id, node.name])),
    [skills.nodes],
  );

  const tiers = useMemo(() => {
    const values = new Set(skills.nodes.map((node) => node.tier));
    return [...values].sort((a, b) => a - b);
  }, [skills.nodes]);

  const layout = useMemo(() => {
    const tierToCol = new Map<number, number>(tiers.map((tier, index) => [tier, index + 1]));
    const positionById = new Map<string, { col: number; row: number }>();
    const nodesByTier = new Map<number, SkillNode[]>();

    for (const node of skills.nodes) {
      const tierNodes = nodesByTier.get(node.tier) ?? [];
      tierNodes.push(node);
      nodesByTier.set(node.tier, tierNodes);
    }

    let maxRows = 1;

    for (const tier of tiers) {
      const tierNodes = (nodesByTier.get(tier) ?? []).sort((a, b) => a.name.localeCompare(b.name));
      const usedRows = new Set<number>();

      for (const node of tierNodes) {
        const depRows = node.dependencies
          .map((depId) => positionById.get(depId)?.row)
          .filter((row): row is number => typeof row === 'number');

        let desiredRow = depRows.length
          ? Math.max(1, Math.round(depRows.reduce((sum, value) => sum + value, 0) / depRows.length))
          : usedRows.size + 1;

        while (usedRows.has(desiredRow)) desiredRow += 1;

        usedRows.add(desiredRow);

        const col = tierToCol.get(node.tier) ?? 1;
        positionById.set(node.id, { col, row: desiredRow });
        maxRows = Math.max(maxRows, desiredRow);
      }
    }

    const edges = skills.nodes.flatMap((node) =>
      node.dependencies
        .map((depId) => {
          const from = positionById.get(depId);
          const to = positionById.get(node.id);
          if (!from || !to) return null;

          const fromNode = skills.nodes.find((candidate) => candidate.id === depId);
          const edgeState = fromNode && toVisualState(fromNode) !== 'locked' ? 'unlocked' : 'locked';

          return {
            key: `${depId}->${node.id}`,
            from,
            to,
            state: edgeState,
          };
        })
        .filter((edge): edge is { key: string; from: { col: number; row: number }; to: { col: number; row: number }; state: 'locked' | 'unlocked' } =>
          Boolean(edge),
        ),
    );

    return { positionById, maxRows, edges };
  }, [skills.nodes, tiers]);

  return (
    <section className="card skills-card">
      <div className="section-header">
        <h2>Skill Tree</h2>
        <span className="muted">
          {skills.activeCount} active · {skills.plannedCount} planned · {skills.lockedCount} locked
        </span>
      </div>

      <div className="skills-grid">
        <div className="skills-tree-stage">
          <div className="skills-legend" aria-label="Skill states legend">
            <span className="legend-item active">Active</span>
            <span className="legend-item in-progress">In progress</span>
            <span className="legend-item planned">Planned</span>
            <span className="legend-item locked">Locked</span>
          </div>

          <div
            className="skills-tree-map"
            style={{
              ['--skills-cols' as string]: String(Math.max(1, tiers.length)),
              ['--skills-rows' as string]: String(Math.max(1, layout.maxRows)),
            }}
            role="list"
            aria-label="Game-style skill tree"
          >
            <svg className="skills-tree-lines" viewBox={`0 0 ${Math.max(1, tiers.length) * 200} ${Math.max(1, layout.maxRows) * 124}`} preserveAspectRatio="none" aria-hidden="true">
              {layout.edges.map((edge) => {
                const startX = (edge.from.col - 0.5) * 200;
                const startY = (edge.from.row - 0.5) * 124;
                const endX = (edge.to.col - 0.5) * 200;
                const endY = (edge.to.row - 0.5) * 124;
                const midX = startX + (endX - startX) * 0.52;

                return (
                  <path
                    key={edge.key}
                    className={`skill-link ${edge.state}`}
                    d={`M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`}
                  />
                );
              })}
            </svg>

            {skills.nodes.map((node) => {
              const pos = layout.positionById.get(node.id) ?? { col: 1, row: 1 };
              const visual = toVisualState(node);
              const isSelected = selected?.id === node.id;

              return (
                <button
                  key={node.id}
                  role="listitem"
                  className={`skill-node ${visual} ${isSelected ? 'selected' : ''}`}
                  onClick={() => setSelectedId(node.id)}
                  title={`${node.name} (${stateLabel(visual)})`}
                  style={{ gridColumn: pos.col, gridRow: pos.row }}
                >
                  <div className="skill-node-header">
                    <span className="skill-node-tier">Tier {node.tier}</span>
                    <span className={`skill-node-state ${visual}`}>{stateLabel(visual)}</span>
                  </div>
                  <div className="skill-node-title">{node.name}</div>
                  <div className="skill-node-meta">Level {node.level} · {Math.round(node.progress * 100)}% complete</div>
                </button>
              );
            })}
          </div>

          <div className="skills-mobile-list" role="list" aria-label="Skill progression list">
            {skills.nodes
              .slice()
              .sort((a, b) => a.tier - b.tier || a.name.localeCompare(b.name))
              .map((node) => {
                const visual = toVisualState(node);
                return (
                  <button
                    key={`mobile-${node.id}`}
                    role="listitem"
                    className={`skill-mobile-item ${visual} ${selected?.id === node.id ? 'selected' : ''}`}
                    onClick={() => setSelectedId(node.id)}
                  >
                    <span className="skill-mobile-tier">Tier {node.tier}</span>
                    <strong>{node.name}</strong>
                    <span className="muted">{stateLabel(visual)} · Level {node.level} · {Math.round(node.progress * 100)}% complete</span>
                  </button>
                );
              })}
          </div>
        </div>

        <aside className="skill-detail" aria-live="polite">
          {selected ? (
            <>
              <h3>{selected.name}</h3>
              <p className="muted">{selected.description}</p>
              <p>{selected.effect}</p>
              <div className="skill-detail-grid">
                <div>
                  <span className="muted">State</span>
                  <strong>{stateLabel(toVisualState(selected))}</strong>
                </div>
                <div>
                  <span className="muted">Tier</span>
                  <strong>{selected.tier}</strong>
                </div>
                <div>
                  <span className="muted">Learned</span>
                  <strong>{selected.learnedAt ?? 'Not learned yet'}</strong>
                </div>
                <div>
                  <span className="muted">Dependencies</span>
                  <strong>
                    {selected.dependencies.length
                      ? selected.dependencies.map((depId) => nodeNameById.get(depId) ?? depId).join(', ')
                      : 'None'}
                  </strong>
                </div>
              </div>
            </>
          ) : (
            <p className="muted">No skills available.</p>
          )}

          <p className="skill-evolution muted">
            Evolution: {skills.evolution.mode} · seed {skills.evolution.deterministicSeed}
          </p>
        </aside>
      </div>
    </section>
  );
}
