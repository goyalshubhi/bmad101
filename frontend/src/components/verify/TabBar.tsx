import { useRef, useCallback } from "react";

type TabBarProps = {
  activeTab: string;
  onTabChange: (tab: string) => void;
  figureCounts: { total: number; pass: number; fail: number };
  checkCounts: { pass: number; fail: number };
  unsignedAssumptionCount: number;
};

const TABS = ["figures", "checks", "assumptions"] as const;

function badgeLabel(tab: string, props: TabBarProps): string {
  if (tab === "figures") {
    return `${props.figureCounts.total} ✓${props.figureCounts.pass} / ✗${props.figureCounts.fail}`;
  }
  if (tab === "checks") {
    return `✓${props.checkCounts.pass} / ✗${props.checkCounts.fail}`;
  }
  return `${props.unsignedAssumptionCount} unsigned`;
}

function tabLabel(tab: string): string {
  return tab.charAt(0).toUpperCase() + tab.slice(1);
}

export default function TabBar(props: TabBarProps) {
  const { activeTab, onTabChange } = props;
  const tabListRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const currentIdx = TABS.indexOf(activeTab as typeof TABS[number]);
      let nextIdx = currentIdx;

      if (e.key === "ArrowRight") {
        nextIdx = (currentIdx + 1) % TABS.length;
        e.preventDefault();
      } else if (e.key === "ArrowLeft") {
        nextIdx = (currentIdx - 1 + TABS.length) % TABS.length;
        e.preventDefault();
      } else {
        return;
      }

      onTabChange(TABS[nextIdx]);
      const buttons = tabListRef.current?.querySelectorAll<HTMLButtonElement>("[role='tab']");
      buttons?.[nextIdx]?.focus();
    },
    [activeTab, onTabChange],
  );

  return (
    <div
      ref={tabListRef}
      role="tablist"
      aria-label="Verification tabs"
      onKeyDown={handleKeyDown}
      style={{
        display: "flex",
        gap: 0,
        borderBottom: "2px solid #e5e7eb",
        marginBottom: 16,
      }}
    >
      {TABS.map((tab) => {
        const isActive = activeTab === tab;
        return (
          <button
            key={tab}
            role="tab"
            type="button"
            aria-selected={isActive}
            aria-controls={`tabpanel-${tab}`}
            id={`tab-${tab}`}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onTabChange(tab)}
            style={{
              padding: "10px 20px",
              fontSize: 14,
              fontWeight: isActive ? 700 : 500,
              color: isActive ? "#2563eb" : "#6b7280",
              background: "none",
              border: "none",
              borderBottom: isActive ? "2px solid #2563eb" : "2px solid transparent",
              marginBottom: -2,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            {tabLabel(tab)}
            <span
              style={{
                fontSize: 12,
                padding: "2px 8px",
                borderRadius: 10,
                background: isActive ? "#eff6ff" : "#f3f4f6",
                color: isActive ? "#2563eb" : "#6b7280",
              }}
            >
              {badgeLabel(tab, props)}
            </span>
          </button>
        );
      })}
    </div>
  );
}
