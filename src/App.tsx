import { AlertTriangle } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { ActivityFeed } from './components/ActivityFeed';
import { CollapsibleSection } from './components/CollapsibleSection';
import { CommandCenter, type CommandCenterItem } from './components/CommandCenter';
import { Findings } from './components/Findings';
import { Header } from './components/Header';
import { JobsTable } from './components/JobsTable';
import { RefreshDiagnosticsPanel } from './components/RefreshDiagnosticsPanel';
import { RuntimeStatus } from './components/RuntimeStatus';
import { SummaryCards } from './components/SummaryCards';
import { SkillsTree } from './components/SkillsTree';
import { TabBar, type DashboardTab } from './components/TabBar';
import { Timeline } from './components/Timeline';
import { TrendCharts } from './components/TrendCharts';
import { WorkstreamBoard } from './components/WorkstreamBoard';
import { useStatus } from './hooks/useStatus';

const TABS: DashboardTab[] = [
  {
    id: 'overview',
    label: 'Overview',
    description: 'High-signal snapshot: current state, workstream lanes, and trend charts.',
  },
  {
    id: 'operations',
    label: 'Operations',
    description: 'Execution plan + scheduler view: timeline blocks and upcoming jobs.',
  },
  {
    id: 'insights',
    label: 'Insights',
    description: 'Activity stream and findings/wins for context and review.',
  },
  {
    id: 'skills',
    label: 'Skills',
    description: 'Game-style growth map with active, planned, and locked capabilities.',
  },
];

function resolveInitialTab(): string {
  if (typeof window === 'undefined') return TABS[0].id;
  const hash = window.location.hash.replace('#tab-', '').trim();
  return TABS.some((tab) => tab.id === hash) ? hash : TABS[0].id;
}

export default function App() {
  const {
    data,
    loading,
    refreshing,
    error,
    errorCode,
    refresh,
    lastRefreshAtMs,
    lastUpdatedLabel,
    freshnessLevel,
    freshnessLabel,
    refreshOutcome,
    sourceMode,
    sourceLabel,
    sourceDetail,
    liveStatusUrl,
    freshnessAgeMinutes,
    lastErrorCode,
    lastErrorMessage,
  } = useStatus();
  const [activeTab, setActiveTab] = useState<string>(resolveInitialTab());
  const [commandCenterOpen, setCommandCenterOpen] = useState(false);
  const [diagnosticsView, setDiagnosticsView] = useState<'fresh' | 'stale'>(
    freshnessLevel === 'stale' ? 'stale' : 'fresh',
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.location.hash = `tab-${activeTab}`;
  }, [activeTab]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const isShortcut = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k';
      if (!isShortcut) return;
      event.preventDefault();
      setCommandCenterOpen((open) => !open);
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const openDiagnosticsView = (view: 'fresh' | 'stale') => {
    setActiveTab('overview');
    setDiagnosticsView(view);
    window.setTimeout(() => {
      document.getElementById('refresh-diagnostics')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 0);
  };

  const commandItems: CommandCenterItem[] = useMemo(() => {
    if (!data) return [];

    const items: CommandCenterItem[] = [];

    for (const tab of TABS) {
      items.push({
        id: `tab-${tab.id}`,
        label: tab.label,
        hint: tab.description,
        group: 'Tabs',
        onSelect: () => setActiveTab(tab.id),
      });
    }

    data.timeline.forEach((item, idx) => {
      items.push({
        id: `timeline-${idx}`,
        label: item.task,
        hint: item.time,
        group: 'Timeline',
        onSelect: () => setActiveTab('operations'),
      });
    });

    data.nextJobs.forEach((job, idx) => {
      items.push({
        id: `job-${idx}`,
        label: job.name,
        hint: `Runs ${job.nextRun}`,
        group: 'Jobs',
        onSelect: () => setActiveTab('operations'),
      });
    });

    data.activity.forEach((activity, idx) => {
      items.push({
        id: `activity-${idx}`,
        label: activity.text,
        hint: `${activity.category.toUpperCase()} · ${activity.time}`,
        group: 'Activity',
        onSelect: () => setActiveTab('insights'),
      });
    });

    data.findings.forEach((finding, idx) => {
      items.push({
        id: `finding-${idx}`,
        label: finding,
        group: 'Findings',
        onSelect: () => setActiveTab('insights'),
      });
    });

    items.push({
      id: 'action-refresh',
      label: 'Force refresh now',
      hint: 'Run an immediate status fetch',
      group: 'Actions',
      onSelect: () => void refresh(),
    });

    items.push({
      id: 'action-copy-gist',
      label: 'Copy live status gist URL',
      hint: liveStatusUrl ?? 'No live source URL available',
      group: 'Actions',
      onSelect: () => {
        if (!liveStatusUrl) return;
        void navigator.clipboard.writeText(liveStatusUrl);
      },
    });

    items.push({
      id: 'action-open-diagnostics',
      label: 'Open current diagnostics view',
      hint: freshnessLevel === 'stale' ? 'Open stale diagnostics view' : 'Open fresh diagnostics view',
      group: 'Actions',
      onSelect: () => openDiagnosticsView(freshnessLevel === 'stale' ? 'stale' : 'fresh'),
    });

    return items;
  }, [data, freshnessLevel, liveStatusUrl, refresh]);

  const content = useMemo(() => {
    if (!data) return null;

    if (activeTab === 'operations') {
      return (
        <>
          <CollapsibleSection
            title="Execution Timeline"
            subtitle="Current day plan blocks"
            defaultOpen={true}
          >
            <Timeline items={data.timeline} hideHeading={true} />
          </CollapsibleSection>

          <CollapsibleSection
            title="Scheduled Jobs"
            subtitle="Next cron actions and status"
            defaultOpen={true}
          >
            <JobsTable jobs={data.nextJobs} hideHeading={true} />
          </CollapsibleSection>
        </>
      );
    }

    if (activeTab === 'insights') {
      return (
        <>
          <CollapsibleSection
            title="Activity Feed"
            subtitle="Filterable operational stream"
            defaultOpen={true}
          >
            <ActivityFeed activity={data.activity ?? []} hideHeading={true} />
          </CollapsibleSection>

          <CollapsibleSection
            title="Findings / Wins"
            subtitle="Recent completed value"
            defaultOpen={false}
          >
            <Findings findings={data.findings} hideHeading={true} />
          </CollapsibleSection>
        </>
      );
    }

    if (activeTab === 'skills') {
      return <SkillsTree skills={data.skills} />;
    }

    return (
      <>
        <RuntimeStatus
          runtime={
            data.runtime ?? {
              status: 'idle',
              isIdle: true,
              activeCount: 0,
              activeRuns: [],
              checkedAtMs: Date.now(),
              source: 'fallback-static',
              revision: 'rtv1-00000000',
              snapshotMode: 'fallback-sanitized',
              degradedReason: 'Runtime payload missing; using safe idle fallback.',
            }
          }
        />
        <RefreshDiagnosticsPanel
          refreshOutcome={refreshOutcome}
          sourceMode={sourceMode}
          sourceLabel={sourceLabel}
          freshnessLevel={freshnessLevel}
          freshnessLabel={freshnessLabel}
          freshnessAgeMinutes={freshnessAgeMinutes}
          lastErrorCode={lastErrorCode}
          lastErrorMessage={lastErrorMessage}
          diagnosticsView={diagnosticsView}
        />
        <SummaryCards data={data} />

        <CollapsibleSection
          title="Now / Next / Done"
          subtitle="Live workstream board"
          defaultOpen={true}
        >
          <WorkstreamBoard
            now={data.workstream?.now ?? []}
            next={data.workstream?.next ?? []}
            done={data.workstream?.done ?? []}
            hideHeading={true}
          />
        </CollapsibleSection>

        <CollapsibleSection
          title="Trend Charts"
          subtitle="Recent run quality + reliability"
          defaultOpen={true}
        >
          <TrendCharts
            jobPoints={data.charts?.jobSuccessTrend ?? []}
            reliabilityPoints={data.charts?.reliabilityTrend ?? []}
          />
        </CollapsibleSection>
      </>
    );
  }, [
    activeTab,
    data,
    diagnosticsView,
    freshnessAgeMinutes,
    freshnessLabel,
    freshnessLevel,
    lastErrorCode,
    lastErrorMessage,
    refreshOutcome,
    sourceLabel,
    sourceMode,
  ]);

  const errorSummary =
    errorCode === 'status-network-error'
      ? 'Status source unreachable.'
      : errorCode === 'status-http-error'
        ? 'Status source returned an HTTP error.'
        : errorCode === 'status-payload-invalid'
          ? 'Status payload is malformed.'
          : errorCode === 'status-url-unavailable'
            ? 'No status source URL is available.'
            : 'Status refresh failed.';

  return (
    <div className={`app-shell ${activeTab === 'skills' ? 'skills-tab-active' : ''}`}>
      <Header
        version={data?.controlRoomVersion ?? '0.0.0'}
        lastUpdatedLabel={lastUpdatedLabel}
        freshnessLevel={freshnessLevel}
        freshnessLabel={freshnessLabel}
        sourceMode={sourceMode}
        sourceLabel={sourceLabel}
        sourceDetail={sourceDetail}
      />

      <TabBar
        tabs={TABS}
        activeTab={activeTab}
        onChange={setActiveTab}
        refreshing={refreshing}
        lastRefreshAtMs={lastRefreshAtMs}
        refreshOutcome={refreshOutcome}
        freshnessLevel={freshnessLevel}
        onRefresh={() => void refresh()}
      />

      <button className="command-center-trigger ghost-btn" onClick={() => setCommandCenterOpen(true)}>
        Command Center <span className="muted">⌘/Ctrl + K</span>
      </button>

      {error && (
        <div className="error-banner">
          <AlertTriangle size={16} />
          <span>
            {errorSummary} {error}
          </span>
        </div>
      )}

      {!data && loading && <div className="card">Loading status…</div>}

      {data && <main className={`dashboard-grid ${activeTab === 'skills' ? 'dashboard-grid-skills' : ''}`}>{content}</main>}

      <CommandCenter open={commandCenterOpen} onClose={() => setCommandCenterOpen(false)} items={commandItems} />
    </div>
  );
}
