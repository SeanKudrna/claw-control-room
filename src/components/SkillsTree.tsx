import { X } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
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
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [isPannable, setIsPannable] = useState(false);
  const mapRef = useRef<HTMLDivElement | null>(null);
  const dragStateRef = useRef<{ pointerId: number; startX: number; startY: number; startLeft: number; startTop: number } | null>(null);

  const selected = useMemo(
    () => skills.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [skills.nodes, selectedNodeId],
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

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const updatePannable = () => {
      setIsPannable(map.scrollWidth > map.clientWidth + 1 || map.scrollHeight > map.clientHeight + 1);
    };

    updatePannable();
    const resizeObserver = new ResizeObserver(() => updatePannable());
    resizeObserver.observe(map);

    return () => resizeObserver.disconnect();
  }, [layout.height, layout.width]);

  useEffect(() => {
    if (!selected) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setSelectedNodeId(null);
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [selected]);

  return (
    <section className="card skills-card">
      <div className="section-header">
        <h2>Skill Tree</h2>
        <span className="muted">
          {skills.activeCount} active · {skills.plannedCount} planned · {skills.lockedCount} locked
        </span>
      </div>

      <div className="skills-tree-stage">
        <div className="skills-legend" aria-label="Skill states legend">
          <span className="legend-item active">Unlocked</span>
          <span className="legend-item in-progress">In progress</span>
          <span className="legend-item planned">Planned</span>
          <span className="legend-item locked">Locked</span>
        </div>

        <div
          ref={mapRef}
          className={`skills-tree-map ${isPannable ? 'is-pannable' : ''} ${dragging ? 'is-dragging' : ''}`}
          role="list"
          aria-label="Game-style skill tree"
          onPointerDown={(event) => {
            const map = mapRef.current;
            if (!map || event.button !== 0 || !isPannable) return;
            if ((event.target as HTMLElement).closest('.skill-node')) return;

            dragStateRef.current = {
              pointerId: event.pointerId,
              startX: event.clientX,
              startY: event.clientY,
              startLeft: map.scrollLeft,
              startTop: map.scrollTop,
            };
            setDragging(true);
            map.setPointerCapture(event.pointerId);
          }}
          onPointerMove={(event) => {
            const map = mapRef.current;
            const dragState = dragStateRef.current;
            if (!map || !dragState || dragState.pointerId !== event.pointerId) return;

            const dx = event.clientX - dragState.startX;
            const dy = event.clientY - dragState.startY;
            map.scrollLeft = dragState.startLeft - dx;
            map.scrollTop = dragState.startTop - dy;
          }}
          onPointerUp={(event) => {
            const map = mapRef.current;
            const dragState = dragStateRef.current;
            if (!map || !dragState || dragState.pointerId !== event.pointerId) return;
            if (map.hasPointerCapture(event.pointerId)) map.releasePointerCapture(event.pointerId);
            dragStateRef.current = null;
            setDragging(false);
          }}
          onPointerCancel={(event) => {
            const map = mapRef.current;
            const dragState = dragStateRef.current;
            if (!map || !dragState || dragState.pointerId !== event.pointerId) return;
            if (map.hasPointerCapture(event.pointerId)) map.releasePointerCapture(event.pointerId);
            dragStateRef.current = null;
            setDragging(false);
          }}
        >
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
                    onClick={() => setSelectedNodeId(node.id)}
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
                  onClick={() => setSelectedNodeId(node.id)}
                >
                  <span className="skill-mobile-tier">Tier {node.tier}</span>
                  <strong>{node.name}</strong>
                  <span className="muted">{stateLabel(visual)} · Level {node.level} · {Math.round(node.progress * 100)}% complete</span>
                </button>
              );
            })}
        </div>

        <p className="skill-evolution muted">
          Evolution: {skills.evolution.mode} · seed {skills.evolution.deterministicSeed}
        </p>
      </div>

      {selected && typeof document !== 'undefined' && createPortal(
        <div
          className="skill-modal-backdrop"
          role="presentation"
          onClick={(event) => {
            if (event.target === event.currentTarget) setSelectedNodeId(null);
          }}
        >
          <section className="skill-modal" role="dialog" aria-modal="true" aria-label="Skill details">
            <header className="skill-modal-header">
              <h3>{selected.name}</h3>
              <button
                type="button"
                className="skill-modal-close"
                onClick={() => setSelectedNodeId(null)}
                aria-label="Close skill details"
              >
                <X size={16} />
              </button>
            </header>

            <p className="muted">{selected.description}</p>
            <p>{selected.effect}</p>

            <dl className="skill-detail-grid">
              <div>
                <dt>State</dt>
                <dd>{stateLabel(toVisualState(selected))}</dd>
              </div>
              <div>
                <dt>Learned</dt>
                <dd>{selected.learnedAt ?? 'Not learned yet'}</dd>
              </div>
              <div>
                <dt>Level / Progress</dt>
                <dd>Level {selected.level} · {Math.round(selected.progress * 100)}%</dd>
              </div>
              <div>
                <dt>Dependencies</dt>
                <dd>
                  {selected.dependencies.length
                    ? selected.dependencies.map((depId) => nodeNameById.get(depId) ?? depId).join(', ')
                    : 'None'}
                </dd>
              </div>
            </dl>
          </section>
        </div>,
        document.body,
      )}
    </section>
  );
}
