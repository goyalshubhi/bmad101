type Assumption = {
  text: string;
  flag_type: string;
  confidence: number;
  source_reference: string;
};

type VizRec = {
  chart_type: string;
  justification: string;
};

export type NarrativeData = {
  id: string;
  story_angle: string;
  narrative_text: string;
  viz_recommendation: VizRec | null;
  assumptions: Assumption[];
  overall_confidence: number;
};

type Props = {
  narrative: NarrativeData;
  isSelected: boolean;
  isExpanded: boolean;
  isModified: boolean;
  onSelect: () => void;
  onClick: () => void;
};

function confidenceColor(score: number): string {
  if (score >= 0.8) return "#16a34a";
  if (score >= 0.6) return "#d97706";
  return "#dc2626";
}

function confidenceLabel(score: number): string {
  if (score >= 0.8) return "high confidence";
  if (score >= 0.6) return "medium confidence";
  return "low confidence";
}

export default function NarrativeCard({ narrative, isSelected, isExpanded, isModified, onSelect, onClick }: Props) {
  const pct = Math.round(narrative.overall_confidence * 100);
  const color = confidenceColor(narrative.overall_confidence);
  const hasInferred = narrative.assumptions.some((a) => a.flag_type === "INFERRED");
  const summary = narrative.narrative_text.length > 200
    ? narrative.narrative_text.slice(0, 200) + "..."
    : narrative.narrative_text;

  return (
    <div
      role="button"
      tabIndex={0}
      aria-expanded={isExpanded}
      onClick={onClick}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(); } }}
      style={{
        width: "100%",
        height: 220,
        border: isSelected ? "2px solid #2563eb" : "1px solid #e5e7eb",
        borderRadius: 12,
        padding: 20,
        display: "flex",
        flexDirection: "column",
        gap: 8,
        background: "#fff",
        cursor: "pointer",
        position: "relative",
        boxSizing: "border-box",
      }}
    >
      {isModified && (
        <span style={{
          position: "absolute", top: 10, left: 10,
          background: "#d97706", color: "#fff", fontSize: 11, fontWeight: 600,
          padding: "2px 8px", borderRadius: 4,
        }}>
          Modified
        </span>
      )}

      {isSelected && (
        <span style={{
          position: "absolute", top: 10, right: 10,
          color: "#2563eb", fontSize: 18, fontWeight: 700,
        }}>
          ✓
        </span>
      )}

      <div style={{ fontWeight: 700, fontSize: 16, color: "#111827", textTransform: "capitalize" }}>
        {narrative.story_angle}
      </div>

      <div style={{ fontSize: 14, color: "#374151", lineHeight: "20px", flex: 1, overflow: "hidden" }}>
        {summary}
      </div>

      {narrative.viz_recommendation && (
        <div style={{ fontSize: 13, color: "#6b7280" }}>
          📊 {narrative.viz_recommendation.chart_type}
        </div>
      )}

      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <span
          aria-label={`Confidence: ${pct}%, ${confidenceLabel(narrative.overall_confidence)}`}
          style={{
            display: "inline-block", fontSize: 13, fontWeight: 600,
            color: "#fff", background: color,
            padding: "2px 10px", borderRadius: 12,
          }}
        >
          {pct}%
        </span>

        <span style={{
          display: "inline-block", fontSize: 13, fontWeight: 500,
          color: "#374151",
          background: hasInferred ? "#fef3c7" : "#f3f4f6",
          padding: "2px 10px", borderRadius: 12,
        }}>
          {narrative.assumptions.length} assumptions
        </span>
      </div>

      <div style={{ marginTop: "auto" }}>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onSelect(); }}
          style={{
            padding: "8px 20px", fontSize: 14, fontWeight: 600,
            color: isSelected ? "#fff" : "#2563eb",
            background: isSelected ? "#2563eb" : "#eff6ff",
            border: "1px solid #2563eb", borderRadius: 6,
            cursor: "pointer",
          }}
        >
          {isSelected ? "✓ Selected" : "Select"}
        </button>
      </div>
    </div>
  );
}
