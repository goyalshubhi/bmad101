type ParsedAnswerLocal = {
  text: string;
  parsed_intent: string;
  confidence: number;
  defaulted: boolean;
};

type QuestionData = {
  id: string;
  template: string;
  context: string;
  suggestion_chips: string[];
  tier: number;
};

type AnsweredCardProps = {
  question: QuestionData;
  answer: ParsedAnswerLocal;
  onEdit: () => void;
};

export default function AnsweredCard({ question, answer, onEdit }: AnsweredCardProps) {
  const isHighConfidence = answer.confidence >= 0.7;
  const confidencePercent = Math.round(answer.confidence * 100);

  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: "14px 20px",
        background: "#fafafa",
        display: "flex",
        alignItems: "flex-start",
        gap: 16,
      }}
    >
      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontSize: 14,
            fontWeight: 500,
            color: "#374151",
            margin: "0 0 4px 0",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {question.template}
        </p>
        {answer.defaulted ? (
          <p style={{ fontSize: 13, color: "#9ca3af", fontStyle: "italic", margin: 0 }}>
            Skipped -- using default
          </p>
        ) : (
          <p style={{ fontSize: 13, color: "#6b7280", margin: 0 }}>{answer.text}</p>
        )}
        {!answer.defaulted && (
          <p style={{ fontSize: 12, color: "#9ca3af", margin: "4px 0 0 0" }}>
            Intent: {answer.parsed_intent}
          </p>
        )}
      </div>

      {/* Confidence badge */}
      <span
        aria-label={`Confidence: ${confidencePercent}%, ${isHighConfidence ? "high confidence" : "low confidence"}`}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
          padding: "3px 10px",
          fontSize: 12,
          fontWeight: 600,
          borderRadius: 9999,
          whiteSpace: "nowrap",
          color: "#fff",
          background: answer.defaulted
            ? "#9ca3af"
            : isHighConfidence
              ? "#16a34a"
              : "#d97706",
        }}
      >
        {answer.defaulted ? "--" : isHighConfidence ? "✓" : "⚠"}{" "}
        {answer.defaulted ? "Default" : `${confidencePercent}%`}
      </span>

      {/* Edit link */}
      <button
        type="button"
        onClick={onEdit}
        style={{
          fontSize: 13,
          fontWeight: 500,
          color: "#2563eb",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          padding: "2px 4px",
          textDecoration: "underline",
        }}
        aria-label={`Edit answer for: ${question.template}`}
      >
        Edit
      </button>
    </div>
  );
}
