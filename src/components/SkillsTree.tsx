import { X } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { computeSkillTreeLayout } from '../lib/skillTreeLayout';
import { getSkillTierProgress } from '../lib/skillsModel';
import type { SkillNode, SkillsPayload } from '../types/status';
import { SkillTierLadder } from './SkillTierLadder';

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

function dedupeDomainNodes(nodes: SkillNode[]): SkillNode[] {
  const merged = new Map<string, SkillNode>();
  for (const node of nodes) {
    const existing = merged.get(node.id);
    if (!existing) {
      merged.set(node.id, node);
      continue;
    }

    const existingTier = getSkillTierProgress(existing).currentTier;
    const incomingTier = getSkillTierProgress(node).currentTier;
    if (incomingTier > existingTier || node.progress > existing.progress) {
      merged.set(node.id, node);
    }
  }

  return [...merged.values()];
}

function toVisualState(node: SkillNode): VisualState {
  const tier = getSkillTierProgress(node);

  if (node.state === 'locked' && tier.currentTier === 0) return 'locked';
  if (node.state === 'active' || tier.currentTier >= tier.maxTier) return 'active';
  if (tier.currentTier > 0 || node.progress > 0) return 'in-progress';
  return 'planned';
}

export function SkillsTree({ skills }: SkillsTreeProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [isPannable, setIsPannable] = useState(false);
  const mapRef = useRef<HTMLDivElement | null>(null);
  const hasAutoCenteredRef = useRef(false);
  const dragStateRef = useRef<{ pointerId: number; startX: number; startY: number; startLeft: number; startTop: number } | null>(null);

  const domainNodes = useMemo(() => dedupeDomainNodes(skills.nodes), [skills.nodes]);

  const counts = useMemo(() => {
    let active = 0;
    let planned = 0;
    let locked = 0;
    for (const node of domainNodes) {
      if (node.state === 'active') active += 1;
      else if (node.state === 'locked') locked += 1;
      else planned += 1;
    }
    return { active, planned, locked };
  }, [domainNodes]);

  const selected = useMemo(
    () => domainNodes.find((node) => node.id === selectedNodeId) ?? null,
    [domainNodes, selectedNodeId],
  );

  const nodeNameById = useMemo(
    () => new Map(domainNodes.map((node) => [node.id, node.name])),
    [domainNodes],
  );

  const layout = useMemo(() => {
    const tierCount = new Set(domainNodes.map((node) => node.tier)).size;
    const width = Math.max(1680, 1360 + domainNodes.length * 150 + tierCount * 90);
    const height = Math.max(1300, 980 + domainNodes.length * 95 + tierCount * 70);
    return computeSkillTreeLayout(domainNodes, width, height);
  }, [domainNodes]);

  useEffect(() => {
    hasAutoCenteredRef.current = false;
  }, [layout.height, layout.width]);

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
    const map = mapRef.current;
    if (!map || hasAutoCenteredRef.current) return;

    const frame = requestAnimationFrame(() => {
      map.scrollLeft = Math.max(0, (layout.width - map.clientWidth) / 2);
      map.scrollTop = Math.max(0, (layout.height - map.clientHeight) / 2);
      hasAutoCenteredRef.current = true;
    });

    return () => cancelAnimationFrame(frame);
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
    <section className="skills-card" data-skills-surface="full-tab">
      <div className="skills-surface-header">
        <div className="section-header skills-surface-title-row">
          <h2>Skill Tree</h2>
          <span className="muted">
            {counts.active} active · {counts.planned} planned · {counts.locked} locked
          </span>
        </div>

        <div className="skills-legend" aria-label="Skill states legend">
          <span className="legend-item active">Unlocked</span>
          <span className="legend-item in-progress">In progress</span>
          <span className="legend-item planned">Planned</span>
          <span className="legend-item locked">Locked</span>
        </div>
      </div>

      <div
        ref={mapRef}
        className={`skills-tree-map ${isPannable ? 'is-pannable' : ''} ${dragging ? 'is-dragging' : ''}`}
        role="list"
        aria-label="Skill domain tree"
        data-map-surface="full-tab"
        onPointerDown={(event) => {
          const map = mapRef.current;
          if (!map || !isPannable) return;
          if (event.pointerType === 'mouse' && event.button !== 0) return;
          if ((event.target as HTMLElement).closest('.skill-node')) return;

          dragStateRef.current = {
            pointerId: event.pointerId,
            startX: event.clientX,
            startY: event.clientY,
            startLeft: map.scrollLeft,
            startTop: map.scrollTop,
          };
          setDragging(true);
          try {
            map.setPointerCapture(event.pointerId);
          } catch {
            // Pointer capture may be unavailable for synthetic or legacy events.
          }
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
          try {
            if (map.hasPointerCapture(event.pointerId)) map.releasePointerCapture(event.pointerId);
          } catch {
            // Ignore release errors for synthetic/legacy pointer paths.
          }
          dragStateRef.current = null;
          setDragging(false);
        }}
        onPointerCancel={(event) => {
          const map = mapRef.current;
          const dragState = dragStateRef.current;
          if (!map || !dragState || dragState.pointerId !== event.pointerId) return;
          try {
            if (map.hasPointerCapture(event.pointerId)) map.releasePointerCapture(event.pointerId);
          } catch {
            // Ignore release errors for synthetic/legacy pointer paths.
          }
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

              const span = Math.hypot(to.x - from.x, to.y - from.y);
              const curvature = Math.max(0.12, Math.min(0.22, 140 / Math.max(span, 1)));
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
            {domainNodes.map((node) => {
              const pos = layout.positions.get(node.id) ?? {
                x: layout.centerX,
                y: layout.centerY,
                depth: 0,
                ringIndex: 0,
                rootId: node.id,
                branchId: node.id,
              };
              const visual = toVisualState(node);
              const isSelected = selected?.id === node.id;
              const tierProgress = getSkillTierProgress(node);

              const nextLabel = tierProgress.nextTier
                ? `Next: Tier ${tierProgress.nextTier}`
                : 'Tier path complete';

              return (
                <button
                  key={node.id}
                  role="listitem"
                  data-node-id={node.id}
                  data-graph-tier={node.tier}
                  data-layout-depth={pos.depth}
                  data-layout-root={pos.rootId}
                  data-layout-branch={pos.branchId}
                  data-layout-ring={pos.ringIndex}
                  className={`skill-node ${visual} ${isSelected ? 'selected' : ''}`}
                  onClick={() => setSelectedNodeId(node.id)}
                  title={`${node.name} (${stateLabel(visual)})`}
                  aria-label={`${node.name}. Tier ${tierProgress.currentTier} of ${tierProgress.maxTier}. ${stateLabel(visual)}.`}
                  style={{
                    left: `${pos.x}px`,
                    top: `${pos.y}px`,
                  }}
                >
                  <span className="skill-node-core" aria-hidden="true" />
                  <div className="skill-node-header">
                    <span className={`skill-node-state ${visual}`}>{stateLabel(visual)}</span>
                    <span className="skill-node-progress">Tier {tierProgress.currentTier}/{tierProgress.maxTier}</span>
                  </div>
                  <div className="skill-node-title">{node.name}</div>
                  <div className="skill-node-meta">{nextLabel}</div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <p className="skill-evolution muted">
        Evolution: {skills.evolution.mode} · seed {skills.evolution.deterministicSeed}
      </p>

      {selected && typeof document !== 'undefined' && createPortal(
        <div
          className="skill-modal-backdrop"
          role="presentation"
          onClick={(event) => {
            if (event.target === event.currentTarget) setSelectedNodeId(null);
          }}
        >
          <section className="skill-modal" role="dialog" aria-modal="true" aria-labelledby="skill-modal-title">
            <header className="skill-modal-header">
              <div>
                <h3 id="skill-modal-title">{selected.name}</h3>
                <p className="muted">Domain progression and tier ladder</p>
              </div>
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

            <SkillTierLadder node={selected} />

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
                <dt>Signal</dt>
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
