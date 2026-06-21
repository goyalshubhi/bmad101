import { useState } from "react";
import type { NarrativeData } from "./NarrativeCard";

type Props = {
  narrative: NarrativeData;
  editedText: string | null;
  onSave: (text: string) => void;
  onClose: () => void;
};

const flagColors: Record<string, { bg: string; color: string }> = {
  EXPLICIT: { bg: "#dcfce7", color: "#166534" },
  PATTERN: { bg: "#dbeafe", color: "#1e40af" },
  INFERRED: { bg: "#fef3c7", color: "#92400e" },
};

export default function NarrativeDetailPanel({ narrative, editedText, onSave, onClose }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(editedText ?? narrative.narrative_text);

  const displayText = editedText ?? narrative.narrative_text;

  const handleSave = () => {
    onSave(draft);
    setEditing(false);
  };

  const handleCancel = () => {
    setDraft(editedText ?? narrative.narrative_text);
    setEditing(false);
  };

  return (
    <div
      role="region"
      aria-label={`Detail panel for ${narrative.story_angle}`}
      style={{
        width: "100%",
        border: "1px solid #e5e7eb",
        borderTop: "none",
        borderRadius: "0 0 12px 12px",
        padding: 24,
        background: "#f9fafb",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#111827" }}>
          {narrative.story_angle}
        </h3>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close detail panel"
          style={{
            background: "none", border: "none", fontSize: 20,
            cursor: "pointer", color: "#6b7280", padding: 4,
          }}
        >
          ✕
        </button>
      </div>

      {editing ? (
        <div style={{ marginBottom: 16 }}>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            autoFocus
            aria-label="Edit narrative text"
            style={{
              width: "100%", minHeight: 120, padding: 12, fontSize: 14,
              lineHeight: "22px", border: "1px solid #d1d5db",
              borderRadius: 8, resize: "vertical", fontFamily: "inherit",
              boxSizing: "border-box",
            }}
          />
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <button
              type="button"
              onClick={handleSave}
              style={{
                padding: "8px 16px", fontSize: 14, fontWeight: 600,
                color: "#fff", background: "#2563eb",
                border: "none", borderRadius: 6, cursor: "pointer",
              }}
            >
              Save
            </button>
            <button
              type="button"
              onClick={handleCancel}
              style={{
                padding: "8px 16px", fontSize: 14, fontWeight: 600,
                color: "#374151", background: "#f3f4f6",
                border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer",
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 14, lineHeight: "22px", color: "#374151", margin: "0 0 8px 0", whiteSpace: "pre-wrap" }}>
            {displayText}
          </p>
          <button
            type="button"
            onClick={() => { setDraft(displayText); setEditing(true); }}
            style={{
              padding: "6px 14px", fontSize: 13, fontWeight: 600,
              color: "#2563eb", background: "#eff6ff",
              border: "1px solid #bfdbfe", borderRadius: 6, cursor: "pointer",
            }}
          >
            Edit
          </button>
        </div>
      )}

      {narrative.assumptions.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ margin: "0 0 8px 0", fontSize: 14, fontWeight: 600, color: "#111827" }}>Assumptions</h4>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {narrative.assumptions.map((a, i) => {
              const flag = flagColors[a.flag_type] || flagColors.EXPLICIT;
              return (
                <li key={i} style={{ fontSize: 13, color: "#374151", marginBottom: 8, lineHeight: "20px" }}>
                  <span style={{
                    display: "inline-block", fontSize: 11, fontWeight: 600,
                    background: flag.bg, color: flag.color,
                    padding: "1px 6px", borderRadius: 4, marginRight: 6,
                  }}>
                    {a.flag_type}
                  </span>
                  {a.text}
                  <span style={{ color: "#9ca3af", marginLeft: 6 }}>
                    ({Math.round(a.confidence * 100)}% · {a.source_reference})
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {narrative.viz_recommendation && (
        <div>
          <h4 style={{ margin: "0 0 8px 0", fontSize: 14, fontWeight: 600, color: "#111827" }}>
            Visualization: {narrative.viz_recommendation.chart_type}
          </h4>
          <p style={{ fontSize: 13, color: "#6b7280", margin: 0 }}>
            {narrative.viz_recommendation.justification}
          </p>
        </div>
      )}
    </div>
  );
}
