import { AlertTriangle } from 'lucide-react';
import { ActivityFeed } from './components/ActivityFeed';
import { Findings } from './components/Findings';
import { Header } from './components/Header';
import { JobsTable } from './components/JobsTable';
import { SummaryCards } from './components/SummaryCards';
import { Timeline } from './components/Timeline';
import { TrendCharts } from './components/TrendCharts';
import { WorkstreamBoard } from './components/WorkstreamBoard';
import { useStatus } from './hooks/useStatus';

export default function App() {
  const { data, loading, error, refresh, lastUpdatedLabel } = useStatus();

  return (
    <div className="app-shell">
      <Header
        version={data?.controlRoomVersion ?? '0.0.0'}
        lastUpdatedLabel={lastUpdatedLabel}
        refreshing={loading}
        onRefresh={() => void refresh()}
      />

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
          <WorkstreamBoard
            now={data.workstream?.now ?? []}
            next={data.workstream?.next ?? []}
            done={data.workstream?.done ?? []}
          />
          <TrendCharts
            jobPoints={data.charts?.jobSuccessTrend ?? []}
            reliabilityPoints={data.charts?.reliabilityTrend ?? []}
          />
          <Timeline items={data.timeline} />
          <JobsTable jobs={data.nextJobs} />
          <ActivityFeed activity={data.activity ?? []} />
          <Findings findings={data.findings} />
        </main>
      )}
    </div>
  );
}
