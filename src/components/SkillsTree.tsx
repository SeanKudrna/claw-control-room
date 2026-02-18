import { useMemo, useState } from 'react';
import { computeSkillTreeLayout } from '../lib/skillTreeLayout';
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

  const layout = useMemo(() => {
    const tierCount = new Set(skills.nodes.map((node) => node.tier)).size;
    const width = Math.max(980, 840 + tierCount * 96);
    const height = Math.max(760, 620 + tierCount * 50);
    return computeSkillTreeLayout(skills.nodes, width, height);
  }, [skills.nodes]);

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
            <span className="legend-item active">Unlocked</span>
            <span className="legend-item in-progress">In progress</span>
            <span className="legend-item planned">Planned</span>
            <span className="legend-item locked">Locked</span>
          </div>

          <div className="skills-tree-map" role="list" aria-label="Game-style skill tree">
            <div className="skills-tree-canvas" style={{ width: layout.width, height: layout.height }}>
              <svg className="skills-tree-lines" viewBox={`0 0 ${layout.width} ${layout.height}`} preserveAspectRatio="none" aria-hidden="true">
                {layout.edges.map((edge) => {
                  const from = layout.positions.get(edge.fromId);
                  const to = layout.positions.get(edge.toId);
                  if (!from || !to) return null;
                  const curvature = 0.16;
                  const cx1 = from.x + (layout.centerX - from.x) * curvature;
                  const cy1 = from.y + (layout.centerY - from.y) * curvature;
                  const cx2 = to.x + (layout.centerX - to.x) * curvature;
                  const cy2 = to.y + (layout.centerY - to.y) * curvature;
                  return (
                    <path
                      key={edge.key}
                      className={`skill-link ${edge.state}`}
                      d={`M ${from.x} ${from.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${to.x} ${to.y}`}
                    />
                  );
                })}
              </svg>

              <div className="skills-tree-nodes">
                {skills.nodes.map((node) => {
                  const pos = layout.positions.get(node.id) ?? { x: layout.centerX, y: layout.centerY };
                  const visual = toVisualState(node);
                  const isSelected = selected?.id === node.id;

                  return (
                    <button
                      key={node.id}
                      role="listitem"
                      data-node-id={node.id}
                      data-tier={node.tier}
                      className={`skill-node ${visual} ${isSelected ? 'selected' : ''}`}
                      onClick={() => setSelectedId(node.id)}
                      title={`${node.name} (${stateLabel(visual)})`}
                      style={{
                        left: `${pos.x}px`,
                        top: `${pos.y}px`,
                      }}
                    >
                      <span className="skill-node-core" aria-hidden="true" />
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
            </div>
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
