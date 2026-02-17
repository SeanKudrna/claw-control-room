import { RefreshCw } from 'lucide-react';

interface HeaderProps {
  lastUpdatedLabel: string;
  refreshing: boolean;
  onRefresh: () => void;
}

export function Header({ lastUpdatedLabel, refreshing, onRefresh }: HeaderProps) {
  return (
    <header className="hero card">
      <div>
        <h1>Claw Control Room</h1>
        <p className="muted">Live window into Claw's day: tasks, progress, findings, and system health.</p>
      </div>

      <div className="hero-meta">
        <div className="updated-pill">Updated: {lastUpdatedLabel}</div>
        <button className="ghost-btn" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw size={16} className={refreshing ? 'spin' : ''} />
          Refresh
        </button>
      </div>
    </header>
  );
}
