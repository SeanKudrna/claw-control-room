import { CheckCircle2, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';

interface HeaderProps {
  version: string;
  lastUpdatedLabel: string;
  freshnessLevel: 'fresh' | 'aging' | 'stale';
  freshnessLabel: string;
  refreshing: boolean;
  lastRefreshAtMs: number | null;
  onRefresh: () => void;
}

type RefreshFeedbackState = 'idle' | 'refreshing' | 'success';

export function Header({
  version,
  lastUpdatedLabel,
  freshnessLevel,
  freshnessLabel,
  refreshing,
  lastRefreshAtMs,
  onRefresh,
}: HeaderProps) {
  const [isPressed, setIsPressed] = useState(false);
  const [feedbackState, setFeedbackState] = useState<RefreshFeedbackState>('idle');

  useEffect(() => {
    if (refreshing) {
      setFeedbackState('refreshing');
      return;
    }

    if (!lastRefreshAtMs) {
      setFeedbackState('idle');
      return;
    }

    setFeedbackState('success');
    const timer = window.setTimeout(() => {
      setFeedbackState('idle');
    }, 1400);

    return () => window.clearTimeout(timer);
  }, [refreshing, lastRefreshAtMs]);

  const buttonLabel =
    feedbackState === 'refreshing'
      ? 'Refreshing…'
      : feedbackState === 'success'
        ? 'Updated'
        : 'Refresh';

  const helperText =
    feedbackState === 'refreshing'
      ? 'Updating data now…'
      : feedbackState === 'success'
        ? 'Updated just now'
        : 'Tap to refresh';

  return (
    <header className="hero card">
      <div>
        <div className="title-row">
          <h1>Claw Control Room</h1>
          <span className="version-pill">v{version}</span>
        </div>
        <p className="muted">Live window into Claw's day: tasks, progress, findings, and system health.</p>
      </div>

      <div className="hero-meta">
        <div className="updated-pill">Updated: {lastUpdatedLabel}</div>
        <div className={`freshness-pill ${freshnessLevel}`}>{freshnessLabel}</div>
        <div className="refresh-control">
          <button
            className={`ghost-btn ${feedbackState !== 'idle' ? `is-${feedbackState}` : ''} ${isPressed ? 'is-pressed' : ''}`.trim()}
            onClick={onRefresh}
            onPointerDown={() => setIsPressed(true)}
            onPointerUp={() => setIsPressed(false)}
            onPointerLeave={() => setIsPressed(false)}
            onPointerCancel={() => setIsPressed(false)}
            disabled={refreshing}
            aria-live="polite"
          >
            {feedbackState === 'success' ? (
              <CheckCircle2 size={16} className="refresh-success-icon" />
            ) : (
              <RefreshCw size={16} className={refreshing ? 'spin' : ''} />
            )}
            {buttonLabel}
          </button>
          <span className={`refresh-helper ${feedbackState}`} aria-live="polite">
            {helperText}
          </span>
        </div>
      </div>
    </header>
  );
}
