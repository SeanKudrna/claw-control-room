interface RefreshDiagnosticsPanelProps {
  refreshOutcome: 'idle' | 'success' | 'error';
  sourceMode: 'configured' | 'fallback';
  sourceLabel: string;
  freshnessLevel: 'fresh' | 'aging' | 'stale';
  freshnessLabel: string;
  freshnessAgeMinutes: number | null;
  lastErrorCode: string | null;
  lastErrorMessage: string | null;
  diagnosticsView: 'fresh' | 'stale';
}

export function RefreshDiagnosticsPanel({
  refreshOutcome,
  sourceMode,
  sourceLabel,
  freshnessLevel,
  freshnessLabel,
  freshnessAgeMinutes,
  lastErrorCode,
  lastErrorMessage,
  diagnosticsView,
}: RefreshDiagnosticsPanelProps) {
  const outcomeLabel =
    refreshOutcome === 'success' ? 'Success' : refreshOutcome === 'error' ? 'Failed' : 'Idle';

  return (
    <section className="card refresh-diagnostics" id="refresh-diagnostics" aria-live="polite">
      <div className="section-header">
        <h2>Refresh Diagnostics</h2>
        <span className={`tiny-pill ${diagnosticsView === 'stale' ? 'error' : 'ok'}`}>
          {diagnosticsView === 'stale' ? 'STALE VIEW' : 'FRESH VIEW'}
        </span>
      </div>

      <dl className="refresh-diagnostics-grid">
        <div>
          <dt>Last outcome</dt>
          <dd>{outcomeLabel}</dd>
        </div>
        <div>
          <dt>Source mode</dt>
          <dd>{sourceMode === 'configured' ? `Live · ${sourceLabel}` : `Fallback · ${sourceLabel}`}</dd>
        </div>
        <div>
          <dt>Freshness</dt>
          <dd>{freshnessLabel}</dd>
        </div>
        <div>
          <dt>Age</dt>
          <dd>{freshnessAgeMinutes == null ? 'Unknown' : `${freshnessAgeMinutes}m`}</dd>
        </div>
        <div className="refresh-diagnostics-span">
          <dt>Last error</dt>
          <dd>
            {lastErrorCode ? (
              <>
                <strong>{lastErrorCode}</strong>
                {lastErrorMessage ? ` · ${lastErrorMessage}` : ''}
              </>
            ) : (
              'None'
            )}
          </dd>
        </div>
      </dl>

      <p className="muted refresh-diagnostics-footnote">
        Current state: {freshnessLevel === 'stale' ? 'stale snapshot window' : 'freshness within expected range'}.
      </p>
    </section>
  );
}
