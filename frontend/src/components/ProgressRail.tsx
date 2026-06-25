import { useNavigate, useParams } from "react-router-dom";

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

const stepRoutes: Record<string, string> = {
  Upload: "validate",
  Questions: "questions",
  "Story Options": "narratives",
  Verify: "verify",
  "Generate Deck": "render",
};

export default function ProgressRail({ steps }: ProgressRailProps) {
  const navigate = useNavigate();
  const { deckId } = useParams<{ deckId: string }>();

  const handleClick = (step: Step) => {
    if (step.status === "inactive") return;
    const route = stepRoutes[step.label];
    if (!route) return;

    if (step.label === "Upload" && !deckId) {
      navigate("/");
      return;
    }

    if (deckId && route) {
      navigate(`/decks/${deckId}/${route}`);
    }
  };

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
        Steps
      </h2>
      {steps.map((step, i) => {
        const isClickable = step.status !== "inactive" && (deckId || step.label === "Upload");
        return (
          <div
            key={i}
            role={isClickable ? "button" : undefined}
            tabIndex={isClickable ? 0 : undefined}
            onClick={() => isClickable && handleClick(step)}
            onKeyDown={(e) => {
              if (isClickable && (e.key === "Enter" || e.key === " ")) {
                e.preventDefault();
                handleClick(step);
              }
            }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "10px 8px",
              borderRadius: 6,
              background: step.status === "active" ? "#eff6ff" : "transparent",
              cursor: isClickable ? "pointer" : "default",
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
        );
      })}

      <div style={{ marginTop: "auto", borderTop: "1px solid #e5e7eb", paddingTop: 12 }}>
        <div
          role="button"
          tabIndex={0}
          onClick={() => navigate("/")}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              navigate("/");
            }
          }}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "10px 8px",
            borderRadius: 6,
            cursor: "pointer",
            color: "#6b7280",
            fontSize: 14,
            fontWeight: 500,
          }}
        >
          ← Back to Home
        </div>
      </div>
    </nav>
  );
}
