interface FindingsProps {
  findings: string[];
  hideHeading?: boolean;
}

export function Findings({ findings, hideHeading = false }: FindingsProps) {
  return (
    <section className="card" aria-label={hideHeading ? 'Recent Findings / Wins' : undefined}>
      {!hideHeading && <h2>Recent Findings / Wins</h2>}
      <ul className="findings">
        {findings.length === 0 && <li className="muted">No findings logged yet.</li>}
        {findings.map((finding, index) => (
          <li key={`${index}-${finding.slice(0, 20)}`}>{finding}</li>
        ))}
      </ul>
    </section>
  );
}
