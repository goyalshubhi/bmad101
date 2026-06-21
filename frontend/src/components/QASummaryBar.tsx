import { useState } from "react";
import { useNavigate } from "react-router-dom";

type QASummaryItem = {
  id: string;
  template: string;
  answer: string;
  parsed_intent: string;
  confidence: number;
};

type Props = {
  deckId: string;
  questions: QASummaryItem[];
};

export default function QASummaryBar({ deckId, questions }: Props) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();

  const handleBackToQuestions = () => {
    if (window.confirm("Changing answers will regenerate narratives. Continue?")) {
      navigate(`/decks/${deckId}/questions`);
    }
  };

  if (questions.length === 0) return null;

  return (
    <div style={{
      border: "1px solid #e5e7eb", borderRadius: 8,
      background: "#f9fafb", marginBottom: 24,
    }}>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-controls="qa-summary-content"
        style={{
          width: "100%", display: "flex", justifyContent: "space-between",
          alignItems: "center", padding: "12px 16px",
          background: "none", border: "none", cursor: "pointer",
          fontSize: 14, fontWeight: 600, color: "#374151",
        }}
      >
        <span>{questions.length} questions answered</span>
        <span style={{ fontSize: 12, transform: expanded ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
          ▼
        </span>
      </button>

      {expanded && (
        <div id="qa-summary-content" style={{ padding: "0 16px 16px" }}>
          <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {questions.map((q) => (
              <li key={q.id} style={{
                padding: "8px 0", borderTop: "1px solid #e5e7eb",
                fontSize: 13, color: "#374151",
              }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{q.template}</div>
                <div style={{ color: "#6b7280" }}>
                  {q.answer || "(skipped)"}
                  {q.parsed_intent && (
                    <span style={{ marginLeft: 8, fontSize: 12, color: "#9ca3af" }}>
                      → {q.parsed_intent}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={handleBackToQuestions}
            style={{
              marginTop: 12, padding: "6px 14px", fontSize: 13,
              color: "#2563eb", background: "none",
              border: "none", cursor: "pointer", textDecoration: "underline",
            }}
          >
            ← Back to Questions
          </button>
        </div>
      )}
    </div>
  );
}
