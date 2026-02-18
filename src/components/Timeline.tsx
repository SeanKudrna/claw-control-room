import type { TimelineItem } from '../types/status';

interface TimelineProps {
  items: TimelineItem[];
  hideHeading?: boolean;
}

function parseClockToMinutes(value: string): number | null {
  const match = value.trim().match(/^(\d{1,2}):(\d{2})$/);
  if (!match) {
    return null;
  }

  const hour = Number(match[1]);
  const minute = Number(match[2]);
  if (!Number.isFinite(hour) || !Number.isFinite(minute) || hour < 0 || hour > 23 || minute < 0 || minute > 59) {
    return null;
  }

  return hour * 60 + minute;
}

function parseTimeRangeToMinutes(rangeText: string): { start: number; end: number } | null {
  const parts = rangeText
    .split(/\s*[\-–—]\s*/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length !== 2) {
    return null;
  }

  const start = parseClockToMinutes(parts[0]);
  const end = parseClockToMinutes(parts[1]);
  if (start == null || end == null) {
    return null;
  }

  return { start, end };
}

function isMinuteWithinRange(nowMinute: number, startMinute: number, endMinute: number): boolean {
  if (startMinute === endMinute) {
    return false;
  }

  if (endMinute > startMinute) {
    return nowMinute >= startMinute && nowMinute < endMinute;
  }

  return nowMinute >= startMinute || nowMinute < endMinute;
}

function getCurrentBlockIndex(items: TimelineItem[]): number {
  const now = new Date();
  const nowMinute = now.getHours() * 60 + now.getMinutes();

  return items.findIndex((item) => {
    const parsedRange = parseTimeRangeToMinutes(item.time);
    if (!parsedRange) {
      return false;
    }

    return isMinuteWithinRange(nowMinute, parsedRange.start, parsedRange.end);
  });
}

export function Timeline({ items, hideHeading = false }: TimelineProps) {
  const currentIndex = getCurrentBlockIndex(items);
  const hasCurrentBlock = currentIndex >= 0;

  return (
    <section className="card" aria-label={hideHeading ? 'Today Timeline' : undefined}>
      {!hideHeading && <h2>Today Timeline</h2>}
      {items.length > 0 && (
        <p className={`timeline-status ${hasCurrentBlock ? 'current' : 'idle'}`}>
          {hasCurrentBlock ? 'Current block highlighted below.' : 'No active timeline block right now.'}
        </p>
      )}
      <ul className="timeline">
        {items.length === 0 && <li className="timeline-item muted">No timeline blocks found.</li>}
        {items.map((item, index) => {
          const isCurrent = index === currentIndex;
          return (
            <li
              className={`timeline-item ${isCurrent ? 'current' : ''}`}
              key={`${item.time}-${index}`}
              aria-current={isCurrent ? 'time' : undefined}
            >
              <div className="timeline-time">{item.time}</div>
              <div className="timeline-task-row">
                <div className="timeline-task">{item.task}</div>
                {isCurrent && <span className="timeline-current-pill">Now</span>}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
