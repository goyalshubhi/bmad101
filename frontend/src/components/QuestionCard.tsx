import { useRef, useEffect } from "react";

type QuestionData = {
  id: string;
  template: string;
  context: string;
  suggestion_chips: string[];
  tier: number;
};

type QuestionCardProps = {
  question: QuestionData;
  onSubmit: (text: string) => void;
  onSkip: () => void;
  initialValue?: string;
  value: string;
  onChange: (value: string) => void;
};

export default function QuestionCard({
  question,
  onSubmit,
  onSkip,
  initialValue,
  value,
  onChange,
}: QuestionCardProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (initialValue !== undefined && value === "") {
      onChange(initialValue);
    }
  }, [initialValue]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    textareaRef.current?.focus();
  }, [question.id]);

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const lineHeight = 20;
    const minHeight = lineHeight * 2;
    const maxHeight = lineHeight * 6;
    const newHeight = Math.min(Math.max(el.scrollHeight, minHeight), maxHeight);
    el.style.height = `${newHeight}px`;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim()) {
        onSubmit(value.trim());
      }
    }
  };

  const handleChipClick = (chip: string) => {
    onChange(chip);
    textareaRef.current?.focus();
  };

  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 24,
        background: "#fff",
        borderLeft: "4px solid #2563eb",
      }}
    >
      {/* Required / Optional badge */}
      <span style={{
        display: "inline-block",
        fontSize: 11,
        fontWeight: 700,
        textTransform: "uppercase",
        letterSpacing: "0.05em",
        padding: "2px 8px",
        borderRadius: 4,
        marginBottom: 8,
        ...(question.tier === 1
          ? { color: "#991b1b", background: "#fef2f2", border: "1px solid #fecaca" }
          : { color: "#6b7280", background: "#f3f4f6", border: "1px solid #e5e7eb" }),
      }}>
        {question.tier === 1 ? "Required" : "Optional"}
      </span>

      {/* Data observation / context */}
      {question.context && (
        <p
          style={{
            fontSize: 13,
            color: "#6b7280",
            fontStyle: "italic",
            margin: "0 0 12px 0",
            lineHeight: 1.5,
          }}
        >
          {question.context}
        </p>
      )}

      {/* Question text */}
      <h2 style={{ fontSize: 16, fontWeight: 600, color: "#111827", margin: "0 0 16px 0" }}>
        {question.template}
      </h2>

      {/* Suggestion chips */}
      {question.suggestion_chips.length > 0 && (
        <div
          style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}
          role="group"
          aria-label="Suggested answers"
        >
          {question.suggestion_chips.map((chip, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleChipClick(chip)}
              style={{
                padding: "6px 14px",
                fontSize: 13,
                fontWeight: 500,
                color: "#2563eb",
                background: "#eff6ff",
                border: "1px solid #bfdbfe",
                borderRadius: 9999,
                cursor: "pointer",
              }}
              onMouseEnter={(e) => {
                (e.target as HTMLButtonElement).style.background = "#dbeafe";
              }}
              onMouseLeave={(e) => {
                (e.target as HTMLButtonElement).style.background = "#eff6ff";
              }}
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onInput={handleInput}
        onKeyDown={handleKeyDown}
        placeholder="Type your answer..."
        aria-label={`Answer for: ${question.template}`}
        style={{
          width: "100%",
          minHeight: 40,
          maxHeight: 120,
          padding: "10px 12px",
          fontSize: 14,
          lineHeight: "20px",
          border: "1px solid #d1d5db",
          borderRadius: 6,
          resize: "none",
          outline: "none",
          fontFamily: "inherit",
          boxSizing: "border-box",
        }}
      />

      {/* Action buttons */}
      <div style={{ display: "flex", gap: 12, marginTop: 12, alignItems: "center" }}>
        <button
          type="button"
          onClick={() => {
            if (value.trim()) onSubmit(value.trim());
          }}
          disabled={!value.trim()}
          style={{
            padding: "8px 20px",
            fontSize: 14,
            fontWeight: 600,
            color: "#fff",
            background: value.trim() ? "#2563eb" : "#d1d5db",
            border: "none",
            borderRadius: 6,
            cursor: value.trim() ? "pointer" : "not-allowed",
          }}
        >
          Submit Answer
        </button>
        <button
          type="button"
          onClick={onSkip}
          style={{
            padding: "8px 16px",
            fontSize: 13,
            fontWeight: 500,
            color: "#6b7280",
            background: "transparent",
            border: "1px solid #d1d5db",
            borderRadius: 6,
            cursor: "pointer",
          }}
        >
          Skip -- use default
        </button>
      </div>
    </div>
  );
}
