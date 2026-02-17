import { ChevronDown } from 'lucide-react';
import type { ReactNode } from 'react';

interface CollapsibleSectionProps {
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

export function CollapsibleSection({
  title,
  subtitle,
  defaultOpen = true,
  children,
}: CollapsibleSectionProps) {
  return (
    <details className="collapse-panel" open={defaultOpen}>
      <summary>
        <div className="collapse-heading">
          <h2>{title}</h2>
          {subtitle && <span className="muted">{subtitle}</span>}
        </div>
        <ChevronDown size={16} className="collapse-chevron" />
      </summary>
      <div className="collapse-content">{children}</div>
    </details>
  );
}
