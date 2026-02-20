import { Search } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

export interface CommandCenterItem {
  id: string;
  label: string;
  hint?: string;
  group: 'Tabs' | 'Timeline' | 'Jobs' | 'Activity' | 'Findings' | 'Actions';
  onSelect: () => void;
}

interface CommandCenterProps {
  open: boolean;
  onClose: () => void;
  items: CommandCenterItem[];
}

function highlightMatch(text: string, query: string): Array<{ text: string; hit: boolean }> {
  const q = query.trim().toLowerCase();
  if (!q) return [{ text, hit: false }];

  const source = text.toLowerCase();
  const index = source.indexOf(q);
  if (index < 0) return [{ text, hit: false }];

  return [
    { text: text.slice(0, index), hit: false },
    { text: text.slice(index, index + q.length), hit: true },
    { text: text.slice(index + q.length), hit: false },
  ].filter((part) => part.text.length > 0);
}

export function CommandCenter({ open, onClose, items }: CommandCenterProps) {
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (!open) {
      setQuery('');
      setActiveIndex(0);
    }
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) => `${item.label} ${item.hint ?? ''} ${item.group}`.toLowerCase().includes(q));
  }, [items, query]);

  useEffect(() => {
    setActiveIndex((idx) => Math.max(0, Math.min(idx, Math.max(0, filtered.length - 1))));
  }, [filtered.length]);

  useEffect(() => {
    if (!open) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setActiveIndex((idx) => (filtered.length === 0 ? 0 : (idx + 1) % filtered.length));
        return;
      }

      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setActiveIndex((idx) => (filtered.length === 0 ? 0 : (idx - 1 + filtered.length) % filtered.length));
        return;
      }

      if (event.key === 'Enter') {
        if (filtered.length === 0) return;
        event.preventDefault();
        filtered[activeIndex]?.onSelect();
        onClose();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [activeIndex, filtered, onClose, open]);

  if (!open) return null;

  return (
    <div className="command-center-backdrop" role="presentation" onClick={onClose}>
      <section
        className="command-center-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Command Center"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="command-center-input-row">
          <Search size={16} />
          <input
            autoFocus={true}
            className="command-center-input"
            placeholder="Search tabs, timeline, jobs, activity, findings, or run quick actions…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <span className="muted command-center-shortcut">Esc</span>
        </div>

        <div className="command-center-list" role="listbox" aria-label="Command results">
          {filtered.length === 0 && (
            <div className="command-center-empty">
              <p>No matching commands.</p>
              <span className="muted">Try another keyword or clear search.</span>
            </div>
          )}

          {filtered.map((item, index) => (
            <button
              key={item.id}
              className={`command-center-item ${index === activeIndex ? 'active' : ''}`}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => {
                item.onSelect();
                onClose();
              }}
              role="option"
              aria-selected={index === activeIndex}
            >
              <div className="command-center-main">
                <span className="command-center-group">{item.group}</span>
                <span>
                  {highlightMatch(item.label, query).map((part, idx) =>
                    part.hit ? <mark key={`${item.id}-label-${idx}`}>{part.text}</mark> : <span key={`${item.id}-label-${idx}`}>{part.text}</span>,
                  )}
                </span>
              </div>
              {item.hint && (
                <span className="muted command-center-hint">
                  {highlightMatch(item.hint, query).map((part, idx) =>
                    part.hit ? <mark key={`${item.id}-hint-${idx}`}>{part.text}</mark> : <span key={`${item.id}-hint-${idx}`}>{part.text}</span>,
                  )}
                </span>
              )}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
