import { useMemo, useState } from 'react';
import type { ActivityItem } from '../types/status';

const ORDER = ['all', 'ui', 'reliability', 'release', 'docs', 'ops'] as const;

type FilterValue = (typeof ORDER)[number];

interface ActivityFeedProps {
  activity: ActivityItem[];
  hideHeading?: boolean;
}

export function ActivityFeed({ activity, hideHeading = false }: ActivityFeedProps) {
  const [filter, setFilter] = useState<FilterValue>('all');

  const filtered = useMemo(() => {
    if (filter === 'all') return activity;
    return activity.filter((item) => item.category === filter);
  }, [activity, filter]);

  const availableFilters = useMemo(() => {
    const present = new Set(activity.map((item) => item.category));
    return ORDER.filter((item) => item === 'all' || present.has(item));
  }, [activity]);

  return (
    <section className="card" aria-label={hideHeading ? 'Activity Feed' : undefined}>
      {!hideHeading && (
        <div className="section-header">
          <h2>Activity Feed</h2>
          <span className="muted">Filterable ops stream from daily memory</span>
        </div>
      )}

      <div className="chip-row">
        {availableFilters.map((value) => (
          <button
            key={value}
            className={`chip ${filter === value ? 'active' : ''}`}
            onClick={() => setFilter(value)}
          >
            {value.toUpperCase()}
          </button>
        ))}
      </div>

      <ul className="activity-list">
        {filtered.length === 0 && <li className="muted">No activity items in this filter.</li>}
        {filtered
          .slice()
          .reverse()
          .map((item, idx) => (
            <li key={`${item.time}-${item.category}-${idx}`} className="activity-item">
              <span className="tiny-pill neutral">{item.time}</span>
              <span className={`tiny-pill ${item.category}`}>{item.category.toUpperCase()}</span>
              <span>{item.text}</span>
            </li>
          ))}
      </ul>
    </section>
  );
}
