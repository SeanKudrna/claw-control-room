export type ReliabilityStatus = 'green' | 'yellow' | 'red' | 'unknown';

export interface TimelineItem {
  time: string;
  task: string;
}

export interface JobItem {
  name: string;
  nextRun: string;
  lastStatus?: string;
}

export interface TrendPoint {
  label: string;
  status: string;
  score: number;
  job?: string;
}

export interface ActivityItem {
  time: string;
  category: string;
  text: string;
}

export interface RuntimeRun {
  jobId: string;
  jobName: string;
  sessionId: string;
  startedAtMs: number;
  startedAtLocal: string;
  runningForMs: number;
  activityType?: 'cron' | 'subagent';
}

export interface StatusPayload {
  generatedAt: string;
  generatedAtLocal: string;
  controlRoomVersion: string;
  currentFocus: string;
  activeWork: string;
  reliability: {
    status: ReliabilityStatus;
  };
  timeline: TimelineItem[];
  nextJobs: JobItem[];
  findings: string[];
  workstream: {
    now: string[];
    next: string[];
    done: string[];
  };
  charts: {
    jobSuccessTrend: TrendPoint[];
    reliabilityTrend: TrendPoint[];
  };
  activity: ActivityItem[];
  runtime: {
    status: 'idle' | 'running';
    isIdle: boolean;
    activeCount: number;
    activeRuns: RuntimeRun[];
    checkedAtMs: number;
    source: string;
  };
}
