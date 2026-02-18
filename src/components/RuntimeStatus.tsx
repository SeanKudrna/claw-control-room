import { Activity, PauseCircle } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import type { StatusPayload } from '../types/status';

function formatDuration(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return [hours, minutes, seconds]
    .map((value) => String(value).padStart(2, '0'))
    .join(':');
}

export function RuntimeStatus({ runtime }: { runtime: StatusPayload['runtime'] }) {
  const [nowMs, setNowMs] = useState<number>(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const rows = useMemo(() => {
    return runtime.activeRuns.map((run) => {
      const activityType = run.activityType ?? 'cron';
      return {
        ...run,
        activityType,
        elapsedLabel: formatDuration(nowMs - run.startedAtMs),
        sourceLabel: activityType === 'interactive' ? 'Interactive' : 'Cron',
        timePrefix: activityType === 'interactive' ? 'last active' : 'since',
      };
    });
  }, [runtime.activeRuns, nowMs]);

  const isIdle = runtime.isIdle || runtime.activeRuns.length === 0;

  return (
    <section className="card runtime-card">
      <div className="section-header">
        <h2>Runtime Status</h2>
        <span className={`runtime-pill ${isIdle ? 'idle' : 'running'}`}>
          {isIdle ? 'IDLE' : `${runtime.activeCount} RUNNING`}
        </span>
      </div>

      {isIdle && (
        <div className="runtime-idle-row">
          <PauseCircle size={16} />
          <span>No active cron or interactive work right now.</span>
        </div>
      )}

      {!isIdle && (
        <ul className="runtime-list">
          {rows.map((run) => (
            <li key={`${run.jobId}-${run.sessionId}`} className="runtime-item">
              <div className="runtime-main">
                <Activity size={14} />
                <strong>{run.jobName}</strong>
                <span className={`runtime-source runtime-source-${run.activityType}`}>
                  {run.sourceLabel}
                </span>
              </div>
              <div className="runtime-meta">
                <span className="runtime-timer">{run.elapsedLabel}</span>
                <span className="muted">{run.timePrefix} {run.startedAtLocal}</span>
              </div>
            </li>
          ))}
        </ul>
      )}

      <p className="muted runtime-footnote">Source: {runtime.source}</p>
    </section>
  );
}
