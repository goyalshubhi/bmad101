type GateStatusBarProps = {
  failedCheckCount: number;
  unsignedAssumptionCount: number;
  onProceedToRender: () => void;
  onBackToNarrative: () => void;
  onDownloadPptx?: () => void;
  mode: "blocking" | "readonly";
  verifiedAt?: string;
};

export default function GateStatusBar({
  failedCheckCount,
  unsignedAssumptionCount,
  onProceedToRender,
  onBackToNarrative,
  onDownloadPptx,
  mode,
  verifiedAt,
}: GateStatusBarProps) {
  const totalBlockers = failedCheckCount + unsignedAssumptionCount;
  const canProceed = totalBlockers === 0;

  return (
    <div
      style={{
        position: "sticky",
        bottom: 0,
        left: 0,
        right: 0,
        padding: "12px 24px",
        background: "#fff",
        borderTop: "1px solid #e5e7eb",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        boxShadow: "0 -2px 8px rgba(0,0,0,0.05)",
        zIndex: 100,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <button
          type="button"
          onClick={onBackToNarrative}
          style={{
            padding: "8px 16px",
            fontSize: 14,
            fontWeight: 500,
            color: "#2563eb",
            background: "none",
            border: "none",
            cursor: "pointer",
            textDecoration: "underline",
          }}
        >
          ← Back to Narrative
        </button>

        {mode === "blocking" && totalBlockers > 0 && (
          <span style={{ fontSize: 13, color: "#991b1b" }}>
            {failedCheckCount > 0 && `${failedCheckCount} failed check${failedCheckCount !== 1 ? "s" : ""}`}
            {failedCheckCount > 0 && unsignedAssumptionCount > 0 && " · "}
            {unsignedAssumptionCount > 0 &&
              `${unsignedAssumptionCount} unsigned assumption${unsignedAssumptionCount !== 1 ? "s" : ""}`}
          </span>
        )}
      </div>

      <div>
        {mode === "readonly" ? (
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <span style={{ fontSize: 14, color: "#16a34a", fontWeight: 600 }}>
              Verified {verifiedAt}
            </span>
            {onDownloadPptx && (
              <button
                type="button"
                onClick={onDownloadPptx}
                aria-label="Download PPTX deck"
                style={{
                  padding: "8px 20px",
                  fontSize: 14,
                  fontWeight: 600,
                  color: "#fff",
                  background: "#2563eb",
                  border: "none",
                  borderRadius: 8,
                  cursor: "pointer",
                }}
              >
                Download PPTX
              </button>
            )}
          </div>
        ) : (
          <button
            type="button"
            onClick={onProceedToRender}
            disabled={!canProceed}
            style={{
              padding: "10px 24px",
              fontSize: 15,
              fontWeight: 700,
              color: "#fff",
              background: canProceed ? "#2563eb" : "#d1d5db",
              border: "none",
              borderRadius: 8,
              cursor: canProceed ? "pointer" : "not-allowed",
            }}
          >
            Proceed to Render →
          </button>
        )}
      </div>
    </div>
  );
}
