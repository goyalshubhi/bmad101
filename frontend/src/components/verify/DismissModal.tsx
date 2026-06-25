import { useState, useEffect, useRef } from "react";

type DismissModalProps = {
  checkName: string;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
};

const FRIENDLY_CHECK_NAMES: Record<string, string> = {
  check_a: "Sum of Parts",
  check_b: "Data Consistency",
  check_c: "Time Series Continuity",
  check_d: "Comparison Validity",
  check_e: "Statistical Significance",
};

export default function DismissModal({ checkName, onConfirm, onCancel }: DismissModalProps) {
  const [reason, setReason] = useState("");
  const [accepted, setAccepted] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const canConfirm = reason.trim().length > 0 && accepted;

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onCancel();
        return;
      }
      if (e.key === "Tab" && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
          'textarea, input, button:not([disabled])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onCancel]);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 3000,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dismiss-modal-heading"
        style={{
          background: "#fff",
          borderRadius: 12,
          padding: 24,
          width: 440,
          maxWidth: "90vw",
          boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
        }}
      >
        <h2
          id="dismiss-modal-heading"
          style={{ fontSize: 18, fontWeight: 700, color: "#111827", marginBottom: 16 }}
        >
          Dismiss: {FRIENDLY_CHECK_NAMES[checkName] || checkName}
        </h2>

        <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#374151", marginBottom: 6 }}>
          Reason for dismissal
        </label>
        <textarea
          ref={textareaRef}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Explain why this check failure is acceptable..."
          style={{
            width: "100%",
            minHeight: 80,
            padding: 10,
            fontSize: 14,
            border: "1px solid #d1d5db",
            borderRadius: 6,
            resize: "vertical",
            boxSizing: "border-box",
          }}
        />

        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginTop: 12,
            fontSize: 14,
            color: "#374151",
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
            style={{ width: 16, height: 16 }}
          />
          I understand this check will be skipped in the final report
        </label>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 20 }}>
          <button
            type="button"
            onClick={onCancel}
            style={{
              padding: "8px 16px",
              fontSize: 14,
              fontWeight: 500,
              color: "#374151",
              background: "#f3f4f6",
              border: "1px solid #d1d5db",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => canConfirm && onConfirm(reason.trim())}
            disabled={!canConfirm}
            style={{
              padding: "8px 16px",
              fontSize: 14,
              fontWeight: 600,
              color: "#fff",
              background: canConfirm ? "#dc2626" : "#d1d5db",
              border: "none",
              borderRadius: 6,
              cursor: canConfirm ? "pointer" : "not-allowed",
            }}
          >
            Confirm Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
