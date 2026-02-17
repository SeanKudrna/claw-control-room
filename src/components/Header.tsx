import { RefreshCw } from 'lucide-react';

interface HeaderProps {
  version: string;
  lastUpdatedLabel: string;
  freshnessLevel: 'fresh' | 'aging' | 'stale';
  freshnessLabel: string;
  refreshing: boolean;
  onRefresh: () => void;
}

export function Header({
  version,
  lastUpdatedLabel,
  freshnessLevel,
  freshnessLabel,
  refreshing,
  onRefresh,
}: HeaderProps) {
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
        <button className="ghost-btn" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw size={16} className={refreshing ? 'spin' : ''} />
          Refresh
        </button>
      </div>
    </header>
  );
}
