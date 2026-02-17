import type { TrendPoint } from '../types/status';

interface TrendChartCardProps {
  title: string;
  subtitle: string;
  points: TrendPoint[];
}

function TrendChartCard({ title, subtitle, points }: TrendChartCardProps) {
  return (
    <article className="card chart-card">
      <div className="section-header">
        <h2>{title}</h2>
        <span className="muted">{subtitle}</span>
      </div>

      {points.length === 0 && <div className="muted">No trend points yet.</div>}

      {points.length > 0 && (
        <div className="mini-chart" role="img" aria-label={`${title} mini chart`}>
          {points.map((point, idx) => (
            <div key={`${point.label}-${idx}`} className="mini-bar-wrap" title={`${point.label} • ${point.status}`}>
              <div
                className={`mini-bar ${point.status.toLowerCase()}`}
                style={{ height: `${Math.max(8, point.score * 100)}%` }}
              />
              <div className="mini-label">{point.label}</div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

export function TrendCharts({
  jobPoints,
  reliabilityPoints,
}: {
  jobPoints: TrendPoint[];
  reliabilityPoints: TrendPoint[];
}) {
  return (
    <section className="trend-grid">
      <TrendChartCard
        title="Job Success Trend"
        subtitle="Recent run outcomes"
        points={jobPoints}
      />
      <TrendChartCard
        title="Reliability Trend"
        subtitle="Watchdog health over recent runs"
        points={reliabilityPoints}
      />
    </section>
  );
}
