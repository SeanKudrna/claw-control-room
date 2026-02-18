import { AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';

export interface DashboardTab {
  id: string;
  label: string;
  description: string;
}

interface TabBarProps {
  tabs: DashboardTab[];
  activeTab: string;
  onChange: (id: string) => void;
  refreshing: boolean;
  lastRefreshAtMs: number | null;
  refreshOutcome: 'idle' | 'success' | 'error';
  freshnessLevel: 'fresh' | 'aging' | 'stale';
  freshnessLabel: string;
  sourceMode: 'configured' | 'fallback';
  errorCode: string | null;
  onRefresh: () => void;
}

type RefreshFeedbackState = 'idle' | 'refreshing' | 'success' | 'error';

export function TabBar({
  tabs,
  activeTab,
  onChange,
  refreshing,
  lastRefreshAtMs,
  refreshOutcome,
  freshnessLevel,
  freshnessLabel,
  sourceMode,
  errorCode,
  onRefresh,
}: TabBarProps) {
  const selected = tabs.find((tab) => tab.id === activeTab) ?? tabs[0];
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

  const staleAfterRefresh = feedbackState === 'success' && freshnessLevel === 'stale';

  const buttonLabel =
    feedbackState === 'refreshing'
      ? 'Refreshing…'
      : feedbackState === 'success'
        ? staleAfterRefresh
          ? 'Fetched'
          : 'Updated'
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
        ? staleAfterRefresh
          ? sourceMode === 'fallback'
            ? `Fetched fallback snapshot — ${freshnessLabel.toLowerCase()}`
            : `Fetched latest available data — ${freshnessLabel.toLowerCase()}`
          : 'Updated just now'
        : feedbackState === 'error'
          ? `Refresh failed (${failureReason}) — showing last known good snapshot`
          : '';

  return (
    <section className="tab-shell card">
      <div className="tab-main-row">
        <div className="tab-row" role="tablist" aria-label="Dashboard sections">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => onChange(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="refresh-control tab-refresh-control">
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

      <p className="tab-description muted">{selected?.description}</p>
    </section>
  );
}
