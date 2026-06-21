import { useEffect, useRef, useCallback } from "react";
import type { FigureTrace, SourceRowsResponse } from "../../types/verify";

type SourceRowsPanelProps = {
  figure: FigureTrace;
  sourceData: SourceRowsResponse;
  onClose: () => void;
};

export default function SourceRowsPanel({ figure, sourceData, onClose }: SourceRowsPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement;
    closeButtonRef.current?.focus();

    return () => {
      previousActiveElement.current?.focus();
    };
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }

      if (e.key === "Tab" && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        );
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    },
    [onClose],
  );

  const handleOverlayClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose],
  );

  const columns = sourceData.rows.length > 0 ? Object.keys(sourceData.rows[0]) : [];

  return (
    <div
      onClick={handleOverlayClick}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0,0,0,0.3)",
        zIndex: 1000,
        display: "flex",
        justifyContent: "flex-end",
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-label={`Source rows for figure ${figure.figure_value}`}
        aria-modal="true"
        onKeyDown={handleKeyDown}
        style={{
          width: "60%",
          maxWidth: 900,
          background: "#fff",
          height: "100%",
          overflowY: "auto",
          boxShadow: "-4px 0 16px rgba(0,0,0,0.1)",
          padding: 24,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "#111827", margin: 0 }}>Source Rows</h2>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close source rows panel"
            style={{
              padding: "4px 12px",
              fontSize: 18,
              background: "none",
              border: "1px solid #d1d5db",
              borderRadius: 6,
              cursor: "pointer",
              color: "#374151",
            }}
          >
            ✕
          </button>
        </div>

        <div
          style={{
            padding: 12,
            background: "#f9fafb",
            borderRadius: 8,
            marginBottom: 16,
            fontSize: 14,
          }}
        >
          <div style={{ marginBottom: 4 }}>
            <span style={{ color: "#6b7280" }}>Figure: </span>
            <span style={{ fontWeight: 600 }}>{sourceData.figure_value}</span>
          </div>
          <div>
            <span style={{ color: "#6b7280" }}>Formula: </span>
            <span style={{ fontFamily: "monospace", fontSize: 13 }}>{sourceData.formula}</span>
          </div>
        </div>

        {sourceData.rows.length === 0 ? (
          <p style={{ color: "#6b7280", fontSize: 14 }}>No source rows available.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
              aria-label="Source data rows"
            >
              <thead>
                <tr style={{ borderBottom: "2px solid #e5e7eb" }}>
                  {columns.map((col) => (
                    <th
                      key={col}
                      scope="col"
                      style={{
                        textAlign: "left",
                        padding: "8px 10px",
                        color: "#374151",
                        fontWeight: 600,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sourceData.rows.map((row, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid #e5e7eb" }}>
                    {columns.map((col) => (
                      <td key={col} style={{ padding: "8px 10px", color: "#374151" }}>
                        {String(row[col] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
