import type { TimelineItem } from '../types/status';

interface TimelineProps {
  items: TimelineItem[];
  hideHeading?: boolean;
}

export function Timeline({ items, hideHeading = false }: TimelineProps) {
  return (
    <section className="card" aria-label={hideHeading ? 'Today Timeline' : undefined}>
      {!hideHeading && <h2>Today Timeline</h2>}
      <ul className="timeline">
        {items.length === 0 && <li className="timeline-item muted">No timeline blocks found.</li>}
        {items.map((item, index) => (
          <li className="timeline-item" key={`${item.time}-${index}`}>
            <div className="timeline-time">{item.time}</div>
            <div className="timeline-task">{item.task}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}
