import { useState } from "react";
import type { AssumptionItem, AssumptionAction } from "../../types/verify";

type AssumptionsListProps = {
  assumptions: AssumptionItem[];
  assumptionActions: AssumptionAction[];
  onAcknowledge: (index: number) => Promise<void>;
  onSignOff: (index: number) => Promise<void>;
  onChallenge: (index: number) => void;
  onReject: (index: number) => Promise<void>;
  mode: "blocking" | "readonly";
};

const FLAG_ORDER: AssumptionItem["flag_type"][] = ["EXPLICIT", "PATTERN", "INFERRED"];

const FLAG_LABELS: Record<string, { label: string; color: string; bgColor: string }> = {
  EXPLICIT: { label: "Explicit", color: "#166534", bgColor: "#dcfce7" },
  PATTERN: { label: "Pattern", color: "#92400e", bgColor: "#fef3c7" },
  INFERRED: { label: "Inferred", color: "#991b1b", bgColor: "#fef2f2" },
};

function getActionForIndex(actions: AssumptionAction[], index: number): AssumptionAction | undefined {
  for (let i = actions.length - 1; i >= 0; i--) {
    if (actions[i].assumption_index === index) return actions[i];
  }
  return undefined;
}

export default function AssumptionsList({
  assumptions,
  assumptionActions,
  onAcknowledge,
  onSignOff,
  onChallenge,
  onReject,
  mode,
}: AssumptionsListProps) {
  const [submittingIndex, setSubmittingIndex] = useState<number | null>(null);
  const [errorIndex, setErrorIndex] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const grouped = FLAG_ORDER.map((flagType) => ({
    flagType,
    items: assumptions
      .map((a, i) => ({ ...a, originalIndex: i }))
      .filter((a) => a.flag_type === flagType),
  })).filter((g) => g.items.length > 0);

  const handleAction = async (index: number, action: () => Promise<void>) => {
    if (submittingIndex !== null) return;
    setSubmittingIndex(index);
    setErrorIndex(null);
    try {
      await action();
    } catch (e) {
      setErrorIndex(index);
      setErrorMessage(e instanceof Error ? e.message : "Action failed");
    } finally {
      setSubmittingIndex(null);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {grouped.map(({ flagType, items }) => {
        const meta = FLAG_LABELS[flagType];
        return (
          <section key={flagType} aria-labelledby={`assumption-group-${flagType}`}>
            <h3
              id={`assumption-group-${flagType}`}
              style={{
                fontSize: 14,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: meta.color,
                marginBottom: 12,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span
                style={{
                  display: "inline-block",
                  padding: "2px 8px",
                  borderRadius: 4,
                  background: meta.bgColor,
                  fontSize: 12,
                }}
              >
                {meta.label}
              </span>
              <span style={{ fontWeight: 400, fontSize: 13, color: "#6b7280" }}>
                ({items.length})
                {flagType === "EXPLICIT" && " — display only, no action needed"}
                {flagType === "PATTERN" && " — requires acknowledgment"}
                {flagType === "INFERRED" && " — requires sign-off"}
              </span>
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {items.map((item) => {
                const existingAction = getActionForIndex(assumptionActions, item.originalIndex);
                const isResolved =
                  existingAction?.action === "acknowledged" ||
                  existingAction?.action === "signed_off";
                const isRejected = existingAction?.action === "rejected";
                const isSubmitting = submittingIndex === item.originalIndex;

                return (
                  <div
                    key={item.originalIndex}
                    style={{
                      padding: "12px 16px",
                      background: isResolved ? "#f0fdf4" : isRejected ? "#fef2f2" : "#f9fafb",
                      borderRadius: 8,
                      border: `1px solid ${isResolved ? "#bbf7d0" : isRejected ? "#fecaca" : "#e5e7eb"}`,
                      opacity: isRejected ? 0.7 : 1,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
                      <div style={{ flex: 1 }}>
                        <p
                          style={{
                            fontSize: 14,
                            color: "#111827",
                            margin: 0,
                            textDecoration: isRejected ? "line-through" : "none",
                          }}
                        >
                          {item.text}
                        </p>
                        <p style={{ fontSize: 12, color: "#6b7280", margin: "4px 0 0 0" }}>
                          Confidence: {Math.round(item.confidence * 100)}% &middot; Source: {item.source_reference}
                        </p>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                        {isResolved && (
                          <span
                            style={{ fontSize: 13, color: "#16a34a", fontWeight: 600 }}
                            aria-label={`Assumption ${existingAction.action === "acknowledged" ? "acknowledged" : "signed off"}`}
                          >
                            {existingAction.action === "acknowledged" ? "Acknowledged" : "Signed off"}
                          </span>
                        )}
                        {isRejected && (
                          <span style={{ fontSize: 13, color: "#dc2626", fontWeight: 600 }}>
                            Rejected
                          </span>
                        )}

                        {mode === "blocking" && !isResolved && !isRejected && flagType === "PATTERN" && (
                          <>
                            <button
                              type="button"
                              onClick={() => handleAction(item.originalIndex, () => onAcknowledge(item.originalIndex))}
                              disabled={isSubmitting}
                              aria-label={`Acknowledge assumption: ${item.text}`}
                              style={{
                                padding: "6px 12px",
                                fontSize: 13,
                                fontWeight: 600,
                                color: "#fff",
                                background: isSubmitting ? "#9ca3af" : "#16a34a",
                                border: "none",
                                borderRadius: 6,
                                cursor: isSubmitting ? "not-allowed" : "pointer",
                              }}
                            >
                              {isSubmitting ? "..." : "Acknowledge"}
                            </button>
                            <button
                              type="button"
                              onClick={() => onChallenge(item.originalIndex)}
                              disabled={isSubmitting}
                              aria-label={`Challenge assumption: ${item.text}`}
                              style={{
                                padding: "6px 12px",
                                fontSize: 13,
                                fontWeight: 600,
                                color: "#dc2626",
                                background: "none",
                                border: "1px solid #fca5a5",
                                borderRadius: 6,
                                cursor: isSubmitting ? "not-allowed" : "pointer",
                              }}
                            >
                              Challenge
                            </button>
                          </>
                        )}

                        {mode === "blocking" && !isResolved && !isRejected && flagType === "INFERRED" && (
                          <>
                            <button
                              type="button"
                              onClick={() => handleAction(item.originalIndex, () => onSignOff(item.originalIndex))}
                              disabled={isSubmitting}
                              aria-label={`Sign off assumption: ${item.text}`}
                              style={{
                                padding: "6px 12px",
                                fontSize: 13,
                                fontWeight: 600,
                                color: "#fff",
                                background: isSubmitting ? "#9ca3af" : "#2563eb",
                                border: "none",
                                borderRadius: 6,
                                cursor: isSubmitting ? "not-allowed" : "pointer",
                              }}
                            >
                              {isSubmitting ? "..." : "Sign off"}
                            </button>
                            <button
                              type="button"
                              onClick={() => handleAction(item.originalIndex, () => onReject(item.originalIndex))}
                              disabled={isSubmitting}
                              aria-label={`Reject assumption: ${item.text}`}
                              style={{
                                padding: "6px 12px",
                                fontSize: 13,
                                fontWeight: 600,
                                color: "#dc2626",
                                background: "none",
                                border: "1px solid #fca5a5",
                                borderRadius: 6,
                                cursor: isSubmitting ? "not-allowed" : "pointer",
                              }}
                            >
                              Reject
                            </button>
                          </>
                        )}
                      </div>
                    </div>

                    {errorIndex === item.originalIndex && (
                      <p style={{ fontSize: 12, color: "#dc2626", margin: "8px 0 0 0" }}>
                        {errorMessage}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        );
      })}

      {assumptions.length === 0 && (
        <div style={{ padding: 32, textAlign: "center", color: "#6b7280", background: "#f9fafb", borderRadius: 8 }}>
          <p style={{ fontSize: 16, fontWeight: 500, marginBottom: 4 }}>No assumptions</p>
          <p style={{ fontSize: 14 }}>No assumptions were extracted from the narrative.</p>
        </div>
      )}
    </div>
  );
}
