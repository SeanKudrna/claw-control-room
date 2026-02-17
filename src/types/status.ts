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

export interface StatusPayload {
  generatedAt: string;
  generatedAtLocal: string;
  currentFocus: string;
  activeWork: string;
  reliability: {
    status: ReliabilityStatus;
  };
  timeline: TimelineItem[];
  nextJobs: JobItem[];
  findings: string[];
}
