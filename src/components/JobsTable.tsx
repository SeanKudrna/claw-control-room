import type { JobItem } from '../types/status';

function statusClass(lastStatus?: string): string {
  const normalized = (lastStatus || 'n/a').toLowerCase();
  if (normalized === 'ok') return 'ok';
  if (normalized === 'error' || normalized === 'failed') return 'error';
  return 'neutral';
}

interface JobsTableProps {
  jobs: JobItem[];
  hideHeading?: boolean;
}

export function JobsTable({ jobs, hideHeading = false }: JobsTableProps) {
  return (
    <section className="card" aria-label={hideHeading ? 'Next Scheduled Jobs' : undefined}>
      {!hideHeading && <h2>Next Scheduled Jobs</h2>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Job</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 && (
              <tr>
                <td colSpan={3} className="muted">No jobs found.</td>
              </tr>
            )}
            {jobs.map((job, idx) => (
              <tr key={`${job.name}-${idx}`}>
                <td>{job.nextRun}</td>
                <td>{job.name}</td>
                <td>
                  <span className={`tiny-pill ${statusClass(job.lastStatus)}`}>{(job.lastStatus || 'n/a').toUpperCase()}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
