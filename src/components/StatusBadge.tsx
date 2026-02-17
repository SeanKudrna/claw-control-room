import type { ReliabilityStatus } from '../types/status';

export function StatusBadge({ status }: { status: ReliabilityStatus }) {
  const normalized = status || 'unknown';
  return <span className={`status-badge ${normalized}`}>{normalized.toUpperCase()}</span>;
}
