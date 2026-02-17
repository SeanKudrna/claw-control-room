import { Activity, Goal, ShieldCheck } from 'lucide-react';
import type { StatusPayload } from '../types/status';
import { StatusBadge } from './StatusBadge';

export function SummaryCards({ data }: { data: StatusPayload }) {
  return (
    <section className="summary-grid">
      <article className="card summary-card">
        <div className="summary-header">
          <Goal size={16} />
          <h2>Current Focus</h2>
        </div>
        <p>{data.currentFocus || 'n/a'}</p>
      </article>

      <article className="card summary-card">
        <div className="summary-header">
          <ShieldCheck size={16} />
          <h2>Reliability</h2>
        </div>
        <StatusBadge status={data.reliability?.status ?? 'unknown'} />
      </article>

      <article className="card summary-card">
        <div className="summary-header">
          <Activity size={16} />
          <h2>Active Work</h2>
        </div>
        <p>{data.activeWork || 'No active task'}</p>
      </article>
    </section>
  );
}
