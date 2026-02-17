interface WorkstreamBoardProps {
  now: string[];
  next: string[];
  done: string[];
  hideHeading?: boolean;
}

function Lane({ title, items, tone }: { title: string; items: string[]; tone: 'now' | 'next' | 'done' }) {
  return (
    <article className={`lane ${tone}`}>
      <h3>{title}</h3>
      <ul>
        {items.length === 0 && <li className="muted">Nothing logged.</li>}
        {items.map((item, idx) => (
          <li key={`${title}-${idx}`}>{item}</li>
        ))}
      </ul>
    </article>
  );
}

export function WorkstreamBoard({ now, next, done, hideHeading = false }: WorkstreamBoardProps) {
  return (
    <section className="card" aria-label={hideHeading ? 'Now / Next / Done' : undefined}>
      {!hideHeading && (
        <div className="section-header">
          <h2>Now / Next / Done</h2>
          <span className="muted">Live workstream view</span>
        </div>
      )}
      <div className="swimlane-grid">
        <Lane title="Now" items={now} tone="now" />
        <Lane title="Next" items={next} tone="next" />
        <Lane title="Done" items={done} tone="done" />
      </div>
    </section>
  );
}
