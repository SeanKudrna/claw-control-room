import { useMemo, useState } from 'react';
import type { ActivityItem } from '../types/status';

const ORDER = ['all', 'ui', 'reliability', 'release', 'docs', 'ops'] as const;
const DEFAULT_VISIBLE_ITEMS = 12;

type FilterValue = (typeof ORDER)[number];

interface ActivityFeedProps {
  activity: ActivityItem[];
  hideHeading?: boolean;
}

export function ActivityFeed({ activity, hideHeading = false }: ActivityFeedProps) {
  const [filter, setFilter] = useState<FilterValue>('all');
  const [expanded, setExpanded] = useState(false);

  const filtered = useMemo(() => {
    if (filter === 'all') return activity;
    return activity.filter((item) => item.category === filter);
  }, [activity, filter]);

  const availableFilters = useMemo(() => {
    const present = new Set(activity.map((item) => item.category));
    return ORDER.filter((item) => item === 'all' || present.has(item));
  }, [activity]);

  const visibleItems = useMemo(() => {
    const reversed = filtered.slice().reverse();
    if (expanded) return reversed;
    return reversed.slice(0, DEFAULT_VISIBLE_ITEMS);
  }, [expanded, filtered]);

  return (
    <section className="card" aria-label={hideHeading ? 'Activity Feed' : undefined}>
      {!hideHeading && (
        <div className="section-header">
          <h2>Activity Feed</h2>
          <span className="muted">Filterable ops stream from daily memory</span>
        </div>
      )}

      <div className="chip-row" role="tablist" aria-label="Activity categories">
        {availableFilters.map((value) => (
          <button
            key={value}
            className={`chip ${filter === value ? 'active' : ''}`}
            onClick={() => {
              setFilter(value);
              setExpanded(false);
            }}
          >
            {value.toUpperCase()}
          </button>
        ))}
      </div>

      <div className="feed-meta-row">
        <span className="muted">Showing {Math.min(visibleItems.length, filtered.length)} of {filtered.length}</span>
        {filtered.length > DEFAULT_VISIBLE_ITEMS && (
          <button className="inline-link-btn" onClick={() => setExpanded((prev) => !prev)}>
            {expanded ? 'Show less' : `Show all (${filtered.length})`}
          </button>
        )}
      </div>

      <ul className="activity-list">
        {filtered.length === 0 && <li className="muted">No activity items in this filter.</li>}
        {visibleItems.map((item, idx) => (
          <li key={`${item.time}-${item.category}-${idx}`} className="activity-item">
            <div className="activity-item-meta">
              <span className="tiny-pill neutral">{item.time}</span>
              <span className={`tiny-pill ${item.category}`}>{item.category.toUpperCase()}</span>
            </div>
            <p className="activity-item-text">{item.text}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
