import { useMemo, useState } from 'react';
import type { ActivityItem } from '../types/status';

const ORDER = ['all', 'ui', 'reliability', 'release', 'docs', 'ops'] as const;
const CATEGORY_ORDER = ORDER.filter((item) => item !== 'all');
const DEFAULT_VISIBLE_ITEMS = 12;

type FilterValue = (typeof ORDER)[number];
type ActivityCategory = (typeof CATEGORY_ORDER)[number];

function normalizeActivityCategory(category: string | null | undefined): ActivityCategory {
  const normalized = (category ?? '').trim().toLowerCase();
  if (CATEGORY_ORDER.includes(normalized as ActivityCategory)) {
    return normalized as ActivityCategory;
  }
  return 'ops';
}

function getDisplayTimeLabel(value: string | null | undefined): string | null {
  const normalized = (value ?? '').trim();
  if (!normalized) {
    return null;
  }

  if (/^n\/?a$/i.test(normalized)) {
    return null;
  }

  return normalized;
}

interface ActivityFeedProps {
  activity: ActivityItem[];
  hideHeading?: boolean;
}

export function ActivityFeed({ activity, hideHeading = false }: ActivityFeedProps) {
  const [filter, setFilter] = useState<FilterValue>('all');
  const [expanded, setExpanded] = useState(false);

  const filtered = useMemo(() => {
    if (filter === 'all') return activity;
    return activity.filter((item) => normalizeActivityCategory(item.category) === filter);
  }, [activity, filter]);

  const availableFilters = useMemo(() => {
    const present = new Set(activity.map((item) => normalizeActivityCategory(item.category)));
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
        {visibleItems.map((item, idx) => {
          const normalizedCategory = normalizeActivityCategory(item.category);
          const displayTime = getDisplayTimeLabel(item.time);
          return (
            <li key={`${item.time}-${item.category}-${idx}`} className="activity-item">
              <div className="activity-item-meta">
                {displayTime && <span className="tiny-pill neutral">{displayTime}</span>}
                <span className={`tiny-pill ${normalizedCategory}`}>{normalizedCategory.toUpperCase()}</span>
              </div>
              <p className="activity-item-text">{item.text}</p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
