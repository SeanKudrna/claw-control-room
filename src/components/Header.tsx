interface HeaderProps {
  version: string;
  lastUpdatedLabel: string;
  freshnessLevel: 'fresh' | 'aging' | 'stale';
  freshnessLabel: string;
  sourceMode: 'configured' | 'fallback';
  sourceLabel: string;
  sourceDetail: string;
}

export function Header({
  version,
  lastUpdatedLabel,
  freshnessLevel,
  freshnessLabel,
  sourceMode,
  sourceLabel,
  sourceDetail,
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
        <div className={`source-pill ${sourceMode}`} title={sourceDetail}>{sourceLabel}</div>
      </div>
    </header>
  );
}
