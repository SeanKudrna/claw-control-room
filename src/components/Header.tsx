import { AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';

interface HeaderProps {
  version: string;
  lastUpdatedLabel: string;
  freshnessLevel: 'fresh' | 'aging' | 'stale';
  freshnessLabel: string;
  refreshing: boolean;
  lastRefreshAtMs: number | null;
  refreshOutcome: 'idle' | 'success' | 'error';
  errorCode: string | null;
  onRefresh: () => void;
}

type RefreshFeedbackState = 'idle' | 'refreshing' | 'success' | 'error';

export function Header({
  version,
  lastUpdatedLabel,
  freshnessLevel,
  freshnessLabel,
  refreshing,
  lastRefreshAtMs,
  refreshOutcome,
  errorCode,
  onRefresh,
}: HeaderProps) {
  const [isPressed, setIsPressed] = useState(false);
  const [feedbackState, setFeedbackState] = useState<RefreshFeedbackState>('idle');

  useEffect(() => {
    if (refreshing) {
      setFeedbackState('refreshing');
      return;
    }

    if (refreshOutcome === 'error') {
      setFeedbackState('error');
      return;
    }

    if (refreshOutcome === 'success' && lastRefreshAtMs) {
      setFeedbackState('success');
      const timer = window.setTimeout(() => {
        setFeedbackState('idle');
      }, 1400);

      return () => window.clearTimeout(timer);
    }

    setFeedbackState('idle');
  }, [refreshing, lastRefreshAtMs, refreshOutcome]);

  const buttonLabel =
    feedbackState === 'refreshing'
      ? 'Refreshing…'
      : feedbackState === 'success'
        ? 'Updated'
        : feedbackState === 'error'
          ? 'Retry refresh'
          : 'Refresh';

  const failureReason =
    errorCode === 'status-network-error'
      ? 'status source unreachable'
      : errorCode === 'status-http-error'
        ? 'status source returned an error'
        : errorCode === 'status-payload-invalid'
          ? 'status payload invalid'
          : errorCode === 'status-url-unavailable'
            ? 'no status source configured'
            : 'unknown refresh error';

  const helperText =
    feedbackState === 'refreshing'
      ? 'Updating data now…'
      : feedbackState === 'success'
        ? 'Updated just now'
        : feedbackState === 'error'
          ? `Refresh failed (${failureReason}) — showing last known good snapshot`
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
            ) : feedbackState === 'error' ? (
              <AlertTriangle size={16} />
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
