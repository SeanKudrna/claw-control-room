import { AlertTriangle } from 'lucide-react';
import { Findings } from './components/Findings';
import { Header } from './components/Header';
import { JobsTable } from './components/JobsTable';
import { SummaryCards } from './components/SummaryCards';
import { Timeline } from './components/Timeline';
import { useStatus } from './hooks/useStatus';

export default function App() {
  const { data, loading, error, refresh, lastUpdatedLabel } = useStatus();

  return (
    <div className="app-shell">
      <Header lastUpdatedLabel={lastUpdatedLabel} refreshing={loading} onRefresh={() => void refresh()} />

      {error && (
        <div className="error-banner">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {!data && loading && <div className="card">Loading status…</div>}

      {data && (
        <main className="dashboard-grid">
          <SummaryCards data={data} />
          <Timeline items={data.timeline} />
          <JobsTable jobs={data.nextJobs} />
          <Findings findings={data.findings} />
        </main>
      )}
    </div>
  );
}
