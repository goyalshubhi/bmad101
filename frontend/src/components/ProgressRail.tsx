type Step = {
  label: string;
  status: "completed" | "active" | "inactive";
};

type ProgressRailProps = {
  steps: Step[];
};

const statusStyles: Record<Step["status"], React.CSSProperties> = {
  completed: { color: "#16a34a", fontWeight: 600 },
  active: { color: "#2563eb", fontWeight: 700 },
  inactive: { color: "#9ca3af", fontWeight: 400 },
};

const statusIcon: Record<Step["status"], string> = {
  completed: "✓",
  active: "●",
  inactive: "○",
};

export default function ProgressRail({ steps }: ProgressRailProps) {
  return (
    <nav
      aria-label="Pipeline progress"
      style={{
        width: 220,
        minHeight: "100vh",
        borderRight: "1px solid #e5e7eb",
        padding: "24px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      <h2 style={{ fontSize: 14, fontWeight: 600, color: "#6b7280", marginBottom: 16, textTransform: "uppercase", letterSpacing: 1 }}>
        Pipeline
      </h2>
      {steps.map((step, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "10px 8px",
            borderRadius: 6,
            background: step.status === "active" ? "#eff6ff" : "transparent",
            ...statusStyles[step.status],
          }}
          aria-current={step.status === "active" ? "step" : undefined}
        >
          <span style={{ fontSize: 16, width: 20, textAlign: "center" }} aria-hidden="true">
            {statusIcon[step.status]}
          </span>
          <span style={{ fontSize: 14 }}>
            {step.label}
            {step.status === "completed" && <span className="sr-only"> (completed)</span>}
          </span>
        </div>
      ))}
    </nav>
  );
}
