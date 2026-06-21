import { useState } from "react";
import type { FigureTrace } from "../../types/verify";

type FiguresTableProps = {
  figureTraces: FigureTrace[];
  onViewSource: (figure: FigureTrace, index: number) => void;
  onEditNarrative: () => void;
  onExcludeRows: (figure: FigureTrace) => void;
};

function statusIcon(status: FigureTrace["match_status"]): { icon: string; color: string; label: string } {
  switch (status) {
    case "exact":
      return { icon: "✓", color: "#16a34a", label: "Matched" };
    case "within_tolerance":
      return { icon: "⚠", color: "#d97706", label: "Within tolerance" };
    case "mismatch":
      return { icon: "✗", color: "#dc2626", label: "Mismatch" };
  }
}

function sortedTraces(traces: FigureTrace[]): (FigureTrace & { originalIndex: number })[] {
  return traces
    .map((t, i) => ({ ...t, originalIndex: i }))
    .sort((a, b) => {
      if (a.match_status === "mismatch" && b.match_status !== "mismatch") return -1;
      if (a.match_status !== "mismatch" && b.match_status === "mismatch") return 1;
      return 0;
    });
}

export default function FiguresTable({
  figureTraces,
  onViewSource,
  onEditNarrative,
  onExcludeRows,
}: FiguresTableProps) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const sorted = sortedTraces(figureTraces);

  return (
    <table
      style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}
      aria-label="Figures verification table"
    >
      <thead>
        <tr style={{ borderBottom: "2px solid #e5e7eb" }}>
          <th scope="col" style={{ textAlign: "left", padding: "10px 12px", color: "#374151", fontWeight: 600 }}>
            Figure
          </th>
          <th scope="col" style={{ textAlign: "left", padding: "10px 12px", color: "#374151", fontWeight: 600 }}>
            Source Rows
          </th>
          <th scope="col" style={{ textAlign: "left", padding: "10px 12px", color: "#374151", fontWeight: 600 }}>
            Formula
          </th>
          <th scope="col" style={{ textAlign: "center", padding: "10px 12px", color: "#374151", fontWeight: 600 }}>
            Status
          </th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((trace) => {
          const { icon, color, label } = statusIcon(trace.match_status);
          const isExpanded = expandedIdx === trace.originalIndex;
          const isMismatch = trace.match_status === "mismatch";

          return (
            <tr key={trace.originalIndex} style={{ borderBottom: "1px solid #e5e7eb" }}>
              <td colSpan={4} style={{ padding: 0 }}>
                <div
                  role={isMismatch ? "button" : undefined}
                  tabIndex={isMismatch ? 0 : undefined}
                  aria-expanded={isMismatch ? isExpanded : undefined}
                  onClick={isMismatch ? () => setExpandedIdx(isExpanded ? null : trace.originalIndex) : undefined}
                  onKeyDown={
                    isMismatch
                      ? (e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            setExpandedIdx(isExpanded ? null : trace.originalIndex);
                          }
                        }
                      : undefined
                  }
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr 1fr auto",
                    cursor: isMismatch ? "pointer" : "default",
                    background: isMismatch ? "#fef2f2" : "transparent",
                  }}
                >
                  <span style={{ padding: "10px 12px" }}>{trace.figure_value}</span>
                  <span style={{ padding: "10px 12px", color: "#6b7280" }}>{trace.source_rows}</span>
                  <span style={{ padding: "10px 12px", color: "#6b7280", fontFamily: "monospace", fontSize: 13 }}>
                    {trace.formula}
                  </span>
                  <span
                    style={{
                      padding: "10px 12px",
                      textAlign: "center",
                      color,
                      fontWeight: 600,
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    <span aria-hidden="true">{icon}</span>
                    <span aria-label={label}>{label}</span>
                  </span>
                </div>

                {isExpanded && isMismatch && (
                  <div
                    style={{
                      padding: "12px 24px",
                      background: "#fef2f2",
                      borderTop: "1px solid #fecaca",
                    }}
                  >
                    <div style={{ display: "flex", gap: 32, marginBottom: 12, fontSize: 13 }}>
                      <div>
                        <span style={{ color: "#6b7280" }}>Narrative figure: </span>
                        <span style={{ fontWeight: 600 }}>{trace.figure_value}</span>
                      </div>
                      <div>
                        <span style={{ color: "#6b7280" }}>Variance: </span>
                        <span style={{ fontWeight: 600, color: "#dc2626" }}>{trace.variance_pct.toFixed(1)}%</span>
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onViewSource(trace, trace.originalIndex);
                        }}
                        style={{
                          padding: "6px 14px",
                          fontSize: 13,
                          fontWeight: 600,
                          color: "#2563eb",
                          background: "#eff6ff",
                          border: "1px solid #bfdbfe",
                          borderRadius: 6,
                          cursor: "pointer",
                        }}
                      >
                        View source rows
                      </button>
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
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onExcludeRows(trace);
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
                        Exclude rows
                      </button>
                    </div>
                  </div>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
