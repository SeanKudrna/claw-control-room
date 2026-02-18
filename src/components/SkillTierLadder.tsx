import type { SkillNode } from '../types/status';
import { getSkillTierLadder, getSkillTierProgress } from '../lib/skillsModel';

interface SkillTierLadderProps {
  node: SkillNode;
}

function tierStateLabel(
  tier: number,
  currentTier: number,
  nextTier: number | null,
): { key: 'complete' | 'current' | 'next' | 'locked'; label: string } {
  if (currentTier > 0 && tier < currentTier) return { key: 'complete', label: 'Complete' };
  if (currentTier > 0 && tier === currentTier) return { key: 'current', label: 'Current tier' };
  if (nextTier !== null && tier === nextTier) return { key: 'next', label: 'Next unlock' };
  return { key: 'locked', label: 'Locked' };
}

export function SkillTierLadder({ node }: SkillTierLadderProps) {
  const progress = getSkillTierProgress(node);
  const ladder = getSkillTierLadder(node);

  const nextUnlockCopy =
    node.nextUnlock ??
    (progress.nextTier
      ? ladder.find((item) => item.tier === progress.nextTier)?.difference ?? null
      : null);

  return (
    <section className="skill-tier-panel" aria-label="Tier progression">
      <div className="skill-tier-progress-summary">
        <span className="skill-tier-pill">Tier {progress.currentTier}/{progress.maxTier}</span>
        <span className="muted">{progress.completedCount} complete</span>
        <span className="muted">
          {progress.nextTier ? `Next unlock: Tier ${progress.nextTier}` : 'Max tier reached'}
        </span>
      </div>

      {nextUnlockCopy && (
        <p className="skill-tier-next-copy muted">
          <strong>Next unlock:</strong> {nextUnlockCopy}
        </p>
      )}

      <ol className="skill-tier-ladder" aria-label={`${node.name} tier ladder`}>
        {ladder.map((entry) => {
          const marker = tierStateLabel(entry.tier, progress.currentTier, progress.nextTier);
          return (
            <li
              key={`${node.id}-tier-${entry.tier}`}
              className={`skill-tier-step ${marker.key}`}
              data-tier-state={marker.key}
              aria-current={marker.key === 'current' ? 'step' : undefined}
            >
              <div className="skill-tier-badge">Tier {entry.tier}</div>
              <div className="skill-tier-copy">
                <h4>{entry.title}</h4>
                <p>{entry.definition}</p>
                <p className="muted">{entry.difference}</p>
              </div>
              <span className={`skill-tier-state ${marker.key}`}>{marker.label}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
