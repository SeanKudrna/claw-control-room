export interface DashboardTab {
  id: string;
  label: string;
  description: string;
}

interface TabBarProps {
  tabs: DashboardTab[];
  activeTab: string;
  onChange: (id: string) => void;
}

export function TabBar({ tabs, activeTab, onChange }: TabBarProps) {
  const selected = tabs.find((tab) => tab.id === activeTab) ?? tabs[0];

  return (
    <section className="tab-shell card">
      <div className="tab-row" role="tablist" aria-label="Dashboard sections">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => onChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <p className="tab-description muted">{selected?.description}</p>
    </section>
  );
}
