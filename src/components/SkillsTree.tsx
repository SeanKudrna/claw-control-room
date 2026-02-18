import { useMemo, useState } from 'react';
import type { SkillNode, SkillsPayload } from '../types/status';

interface SkillsTreeProps {
  skills: SkillsPayload;
}

function stateLabel(state: SkillNode['state']): string {
  if (state === 'active') return 'Active';
  if (state === 'planned') return 'Planned';
  return 'Locked';
}

export function SkillsTree({ skills }: SkillsTreeProps) {
  const [selectedId, setSelectedId] = useState<string>(skills.nodes[0]?.id ?? '');

  const selected = useMemo(
    () => skills.nodes.find((node) => node.id === selectedId) ?? skills.nodes[0] ?? null,
    [skills.nodes, selectedId],
  );

  return (
    <section className="card skills-card">
      <div className="section-header">
        <h2>Skill Tree</h2>
        <span className="muted">
          {skills.activeCount} active · {skills.plannedCount} planned · {skills.lockedCount} locked
        </span>
      </div>

      <div className="skills-grid">
        <div className="skills-tree" role="list" aria-label="Skill tree nodes">
          {skills.nodes.map((node) => (
            <button
              key={node.id}
              role="listitem"
              className={`skill-node ${node.state} ${selected?.id === node.id ? 'selected' : ''}`}
              onClick={() => setSelectedId(node.id)}
              title={`${node.name} (${stateLabel(node.state)})`}
            >
              <div className="skill-node-title">{node.name}</div>
              <div className="skill-node-meta">Lv {node.level} · {Math.round(node.progress * 100)}%</div>
            </button>
          ))}
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
                  <strong>{stateLabel(selected.state)}</strong>
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
                  <strong>{selected.dependencies.length ? selected.dependencies.join(', ') : 'None'}</strong>
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
