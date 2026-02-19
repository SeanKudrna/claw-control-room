import { Activity, PauseCircle, X } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import type { RuntimeRun, StatusPayload } from '../types/status';

const BASELINE_MODEL = 'gpt-5.3-codex';
const BASELINE_THINKING = 'high';

function formatDuration(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return [hours, minutes, seconds]
    .map((value) => String(value).padStart(2, '0'))
    .join(':');
}

function normalizeModelKey(value?: string): string {
  if (!value || typeof value !== 'string') return '';
  const trimmed = value.trim().toLowerCase();
  if (!trimmed) return '';
  const suffix = trimmed.split('/').filter(Boolean).pop() ?? '';
  return suffix;
}

function normalizeThinking(value?: string): string {
  if (!value || typeof value !== 'string') return '';
  const normalized = value.trim().toLowerCase().replace(/[-\s]+/g, '_');
  if (!normalized) return '';
  if (normalized === 'max' || normalized === 'maximum' || normalized === 'very_high') return 'extra_high';
  if (normalized === 'extra_high') return 'extra_high';
  if (normalized === 'minimal' || normalized === 'min') return 'minimal';
  if (normalized === 'low' || normalized === 'medium' || normalized === 'high') return normalized;
  return normalized;
}

function formatThinkingLevel(value?: string): string {
  const normalized = normalizeThinking(value);
  if (!normalized) return 'Not reported';
  if (normalized === 'extra_high') return 'Extra high';
  return normalized.charAt(0).toUpperCase() + normalized.slice(1).replace(/_/g, ' ');
}

function formatModel(value?: string): string {
  if (!value || typeof value !== 'string') return 'Not reported';
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : 'Not reported';
}

function baselineIndicator(run: Pick<RuntimeRun, 'model' | 'thinking'>): {
  tone: 'match' | 'off' | 'unknown';
  label: string;
} {
  const modelKey = normalizeModelKey(run.model);
  const thinking = normalizeThinking(run.thinking);

  if (!modelKey || !thinking) {
    return {
      tone: 'unknown',
      label: 'Baseline check unavailable (model/thinking metadata missing).',
    };
  }

  if (modelKey === BASELINE_MODEL && thinking === BASELINE_THINKING) {
    return {
      tone: 'match',
      label: '✓ Baseline match: gpt-5.3-codex + high',
    };
  }

  return {
    tone: 'off',
    label: '⚠ Non-baseline runtime (target: gpt-5.3-codex + high)',
  };
}

type RuntimeRow = RuntimeRun & {
  activityType: 'cron' | 'subagent';
  elapsedLabel: string;
  sourceLabel: string;
  timePrefix: string;
};

export function RuntimeStatus({ runtime }: { runtime: StatusPayload['runtime'] }) {
  const [nowMs, setNowMs] = useState<number>(() => Date.now());
  const [selectedRun, setSelectedRun] = useState<RuntimeRow | null>(null);
  const lastTriggerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!selectedRun) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSelectedRun(null);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [selectedRun]);

  useEffect(() => {
    if (selectedRun) return;
    if (!lastTriggerRef.current) return;
    lastTriggerRef.current.focus();
  }, [selectedRun]);

  const rows = useMemo(() => {
    return runtime.activeRuns.map((run) => {
      const activityType = run.activityType ?? 'cron';
      const sessionKey = run.sessionKey || run.sessionId;
      const summary = run.summary || run.jobName;
      const sourceLabel = activityType === 'subagent' ? 'Background' : 'Cron';
      return {
        ...run,
        sessionKey,
        summary,
        activityType,
        elapsedLabel: formatDuration(nowMs - run.startedAtMs),
        sourceLabel,
        timePrefix: 'since',
      };
    });
  }, [runtime.activeRuns, nowMs]);

  const isIdle = runtime.isIdle || runtime.activeRuns.length === 0;
  const selectedBaseline = selectedRun ? baselineIndicator(selectedRun) : null;

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
          <span>No active background work right now.</span>
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
              <button
                type="button"
                className="runtime-detail-btn"
                onClick={(event) => {
                  lastTriggerRef.current = event.currentTarget;
                  setSelectedRun(run);
                }}
                aria-label={`Show runtime details for ${run.jobName}`}
              >
                Details
              </button>
            </li>
          ))}
        </ul>
      )}

      {selectedRun && typeof document !== 'undefined' && createPortal(
        <div
          className="runtime-modal-backdrop"
          role="presentation"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedRun(null);
            }
          }}
        >
          <section className="runtime-modal" role="dialog" aria-modal="true" aria-label="Runtime task details">
            <header className="runtime-modal-header">
              <h3>{selectedRun.jobName}</h3>
              <button
                type="button"
                className="runtime-modal-close"
                onClick={() => setSelectedRun(null)}
                aria-label="Close runtime details"
              >
                <X size={16} />
              </button>
            </header>

            <dl className="runtime-detail-grid">
              <div>
                <dt>Source type</dt>
                <dd>{selectedRun.sourceLabel}</dd>
              </div>
              <div>
                <dt>Session</dt>
                <dd>{selectedRun.sessionId}</dd>
              </div>
              <div>
                <dt>Session key</dt>
                <dd>{selectedRun.sessionKey || selectedRun.sessionId}</dd>
              </div>
              <div>
                <dt>Started</dt>
                <dd>{selectedRun.startedAtLocal}</dd>
              </div>
              <div>
                <dt>Elapsed</dt>
                <dd>{selectedRun.elapsedLabel}</dd>
              </div>
              <div>
                <dt>Model used</dt>
                <dd>{formatModel(selectedRun.model)}</dd>
              </div>
              <div>
                <dt>Thinking level</dt>
                <dd>{formatThinkingLevel(selectedRun.thinking)}</dd>
              </div>
              <div>
                <dt>Baseline target</dt>
                <dd>
                  <span className={`runtime-baseline-pill ${selectedBaseline?.tone ?? 'unknown'}`}>
                    {selectedBaseline?.label ?? 'Baseline check unavailable (model/thinking metadata missing).'}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Task summary</dt>
                <dd>{selectedRun.summary || selectedRun.jobName}</dd>
              </div>
            </dl>
          </section>
        </div>,
        document.body,
      )}

      <p className="muted runtime-footnote">
        Source: {runtime.source} · Revision: {runtime.revision} · Mode: {runtime.snapshotMode}
      </p>
      {runtime.degradedReason && (
        <p className="muted runtime-footnote">Degraded: {runtime.degradedReason}</p>
      )}
    </section>
  );
}
