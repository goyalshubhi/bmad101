import { useState } from "react";
import type { CheckResult } from "../../types/verify";

type ChecksListProps = {
  checks: Record<string, CheckResult>;
  onApplyFix: (checkName: string) => Promise<void>;
  onDismiss: (checkName: string) => void;
  onEditNarrative: () => void;
};

const CHECK_NAMES: Record<string, string> = {
  check_a: "A — Sum of Parts",
  check_b: "B — Data Consistency",
  check_c: "C — Time Series Continuity",
  check_d: "D — Comparison Validity",
  check_e: "E — Statistical Significance",
};

function statusDisplay(checkName: string, result: CheckResult): { icon: string; label: string; color: string; bg: string } {
  if (result.status === "dismissed") {
    return { icon: "⊘", label: "DISMISSED", color: "#6b7280", bg: "#f9fafb" };
  }
  if (result.status === "pass") {
    return { icon: "✓", label: "PASS", color: "#16a34a", bg: "#f0fdf4" };
  }
  if (checkName === "check_e") {
    return { icon: "⚠", label: "WEAK", color: "#d97706", bg: "#fffbeb" };
  }
  return { icon: "✗", label: "FAIL", color: "#dc2626", bg: "#fef2f2" };
}

export default function ChecksList({ checks, onApplyFix, onDismiss, onEditNarrative }: ChecksListProps) {
  const [expandedCheck, setExpandedCheck] = useState<string | null>(null);
  const [submittingCheck, setSubmittingCheck] = useState<string | null>(null);
  const [errorCheck, setErrorCheck] = useState<{ key: string; message: string } | null>(null);
  const checkEntries = Object.entries(checks);

  const handleApplyFix = async (key: string) => {
    if (submittingCheck) return;
    setSubmittingCheck(key);
    setErrorCheck(null);
    try {
      await onApplyFix(key);
    } catch (e) {
      setErrorCheck({ key, message: e instanceof Error ? e.message : "Failed to apply fix" });
    } finally {
      setSubmittingCheck(null);
    }
  };

  return (
    <div role="list" aria-label="Reconciliation checks">
      {checkEntries.map(([key, result]) => {
        const { icon, label, color, bg } = statusDisplay(key, result);
        const isFailed = result.status === "fail";
        const isDismissed = result.status === "dismissed";
        const isExpanded = expandedCheck === key;
        const isCheckE = key === "check_e";
        const isSubmitting = submittingCheck === key;

        return (
          <div
            key={key}
            role="listitem"
            style={{
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              marginBottom: 8,
              overflow: "hidden",
            }}
          >
            <div
              role={isFailed ? "button" : undefined}
              tabIndex={isFailed ? 0 : undefined}
              aria-expanded={isFailed ? isExpanded : undefined}
              onClick={isFailed ? () => setExpandedCheck(isExpanded ? null : key) : undefined}
              onKeyDown={
                isFailed
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setExpandedCheck(isExpanded ? null : key);
                      }
                    }
                  : undefined
              }
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "12px 16px",
                background: bg,
                cursor: isFailed ? "pointer" : "default",
                transition: "background 0.3s",
              }}
            >
              <span style={{ fontWeight: 600, fontSize: 14, color: "#111827" }}>
                {CHECK_NAMES[key] || key}
              </span>
              <span
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  fontWeight: 700,
                  fontSize: 13,
                  color,
                  transition: "color 0.3s, opacity 0.3s",
                }}
              >
                <span aria-hidden="true">{icon}</span>
                <span>{label}</span>
                {isFailed && <span style={{ color: "#6b7280", fontWeight: 400 }}>{isExpanded ? "▲" : "▼"}</span>}
              </span>
            </div>

            {isDismissed && result.dismissed_reason && (
              <div style={{ padding: "8px 16px", borderTop: "1px solid #e5e7eb", background: "#f9fafb", fontSize: 13, color: "#6b7280" }}>
                Dismissed: {result.dismissed_reason}
              </div>
            )}

            {isExpanded && isFailed && (
              <div style={{ padding: "12px 16px", borderTop: "1px solid #e5e7eb", background: "#fff" }}>
                <div style={{ display: "flex", gap: 32, marginBottom: 12, fontSize: 13 }}>
                  <div>
                    <span style={{ color: "#6b7280" }}>Expected: </span>
                    <span style={{ fontWeight: 600 }}>{String(result.expected ?? "N/A")}</span>
                  </div>
                  <div>
                    <span style={{ color: "#6b7280" }}>Actual: </span>
                    <span style={{ fontWeight: 600, color: "#dc2626" }}>{String(result.actual ?? "N/A")}</span>
                  </div>
                </div>

                {result.fix_suggestion && (
                  <div
                    style={{
                      padding: "8px 12px",
                      background: "#f9fafb",
                      borderRadius: 6,
                      fontSize: 13,
                      color: "#374151",
                      marginBottom: 12,
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>Suggested fix: </span>
                    {result.fix_suggestion}
                  </div>
                )}

                {isCheckE && (
                  <div
                    style={{
                      padding: "8px 12px",
                      background: "#fffbeb",
                      borderRadius: 6,
                      fontSize: 13,
                      color: "#92400e",
                      marginBottom: 12,
                    }}
                  >
                    R² value indicates a weak trend. The statistical relationship may not be significant.
                  </div>
                )}

                {errorCheck?.key === key && (
                  <div style={{ padding: "8px 12px", background: "#fef2f2", borderRadius: 6, fontSize: 13, color: "#991b1b", marginBottom: 12 }}>
                    {errorCheck.message}
                  </div>
                )}

                <div style={{ display: "flex", gap: 8 }}>
                  {isCheckE ? (
                    <button
                      type="button"
                      disabled={!!submittingCheck}
                      onClick={(e) => {
                        e.stopPropagation();
                        onDismiss(key);
                      }}
                      style={{
                        padding: "6px 14px",
                        fontSize: 13,
                        fontWeight: 600,
                        color: "#d97706",
                        background: "#fffbeb",
                        border: "1px solid #fcd34d",
                        borderRadius: 6,
                        cursor: submittingCheck ? "not-allowed" : "pointer",
                        opacity: submittingCheck ? 0.6 : 1,
                      }}
                    >
                      Acknowledge weak trend
                    </button>
                  ) : (
                    <>
                      <button
                        type="button"
                        disabled={!!submittingCheck}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleApplyFix(key);
                        }}
                        style={{
                          padding: "6px 14px",
                          fontSize: 13,
                          fontWeight: 600,
                          color: "#2563eb",
                          background: "#eff6ff",
                          border: "1px solid #bfdbfe",
                          borderRadius: 6,
                          cursor: submittingCheck ? "not-allowed" : "pointer",
                          opacity: submittingCheck ? 0.6 : 1,
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                        }}
                      >
                        {isSubmitting && (
                          <span
                            style={{
                              display: "inline-block",
                              width: 14,
                              height: 14,
                              border: "2px solid #bfdbfe",
                              borderTopColor: "#2563eb",
                              borderRadius: "50%",
                              animation: "spin 1s linear infinite",
                            }}
                          />
                        )}
                        Apply fix
                      </button>
                      <button
                        type="button"
                        disabled={!!submittingCheck}
                        onClick={(e) => {
                          e.stopPropagation();
                          onDismiss(key);
                        }}
                        style={{
                          padding: "6px 14px",
                          fontSize: 13,
                          fontWeight: 600,
                          color: "#374151",
                          background: "#f3f4f6",
                          border: "1px solid #d1d5db",
                          borderRadius: 6,
                          cursor: submittingCheck ? "not-allowed" : "pointer",
                          opacity: submittingCheck ? 0.6 : 1,
                        }}
                      >
                        Dismiss
                      </button>
                    </>
                  )}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onEditNarrative();
                    }}
                    style={{
                      padding: "6px 14px",
                      fontSize: 13,
                      fontWeight: 600,
                      color: "#374151",
                      background: "#f3f4f6",
                      border: "1px solid #d1d5db",
                      borderRadius: 6,
                      cursor: "pointer",
                    }}
                  >
                    Edit narrative
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
