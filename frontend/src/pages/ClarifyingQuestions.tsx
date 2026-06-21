import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppShell from "../layouts/AppShell";
import DataContextStrip from "../components/DataContextStrip";
import QuestionCard from "../components/QuestionCard";
import AnsweredCard from "../components/AnsweredCard";
import { apiFetch, ApiError } from "../api/client";
import { estimateConfidence, type EstimatedAnswer } from "../utils/confidenceEstimator";

/* ---- Types (mirrors backend Pydantic schemas) ---- */

type QuestionResponse = {
  id: string;
  template: string;
  context: string;
  suggestion_chips: string[];
  tier: number;
};

type QuestionsListResponse = {
  session_id: string;
  questions: QuestionResponse[];
};

type IngestStatus = {
  ingest_job_id: string;
  schema: {
    columns: { name: string; type: string; nullable_pct: number }[];
    row_count: number;
  } | null;
  quality_report: {
    status: string;
    issues: { severity: string; description: string; count: number; sample_rows: number[] }[];
  } | null;
  status: string;
  validated_at: string | null;
};

type ParsedAnswerLocal = {
  text: string;
  parsed_intent: string;
  confidence: number;
  defaulted: boolean;
};

type AnswerSubmitResponse = {
  parsed: {
    question_id: string;
    raw_answer: string;
    parsed_intent: string;
    confidence: number;
    defaulted: boolean;
  }[];
  ready_to_generate: boolean;
};

/* ---- Pipeline steps ---- */

const pipelineSteps = () => [
  { label: "Ingest", status: "completed" as const },
  { label: "Questions", status: "active" as const },
  { label: "Narratives", status: "inactive" as const },
  { label: "Verify", status: "inactive" as const },
  { label: "Render", status: "inactive" as const },
];

/* ---- Component ---- */

export default function ClarifyingQuestions() {
  const { deckId } = useParams<{ deckId: string }>();
  const navigate = useNavigate();

  // Data loading
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ingestData, setIngestData] = useState<IngestStatus | null>(null);
  const [questions, setQuestions] = useState<QuestionResponse[]>([]);
  const [sessionId, setSessionId] = useState<string>("");

  // Question flow state
  const [activeQuestionIndex, setActiveQuestionIndex] = useState(0);
  const [answeredQuestions, setAnsweredQuestions] = useState<Map<string, ParsedAnswerLocal>>(new Map());
  const [followUpActive, setFollowUpActive] = useState(false);
  const [followUpText, setFollowUpText] = useState("");
  const [currentAnswerText, setCurrentAnswerText] = useState("");

  // Submit state
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Aria live ref
  const liveRegionRef = useRef<HTMLDivElement>(null);

  const announce = (message: string) => {
    if (liveRegionRef.current) {
      liveRegionRef.current.textContent = message;
    }
  };

  /* ---- Data fetching ---- */

  useEffect(() => {
    if (!deckId) return;
    let cancelled = false;

    (async () => {
      try {
        const [ingest, questionsData] = await Promise.all([
          apiFetch<IngestStatus>(`/api/v1/decks/${deckId}/ingest-status`),
          apiFetch<QuestionsListResponse>(`/api/v1/decks/${deckId}/questions`),
        ]);

        if (cancelled) return;

        // Guard: must have validated ingest
        const validStatuses = ["CLEAN", "ISSUES_ACKNOWLEDGED"];
        if (!validStatuses.includes(ingest.status)) {
          setError("Data has not been validated yet. Please complete validation first.");
          setLoading(false);
          return;
        }

        setIngestData(ingest);
        setQuestions(questionsData.questions);
        setSessionId(questionsData.session_id);
        setError(null);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : "Failed to load questions");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [deckId]);

  /* ---- Derived state ---- */

  const activeQuestion = questions[activeQuestionIndex] as QuestionResponse | undefined;
  const allQuestionsHandled = questions.length > 0 && questions.every(
    (q) => answeredQuestions.has(q.id)
  );
  const tier1Resolved = questions
    .filter((q) => q.tier === 1)
    .every((q) => answeredQuestions.has(q.id));
  const canGenerate = tier1Resolved;

  /* ---- Handlers ---- */

  const handleSubmitAnswer = (text: string) => {
    if (!activeQuestion) return;

    const estimate: EstimatedAnswer = estimateConfidence(text);

    if (estimate.confidence >= 0.7) {
      // High confidence -- collapse and advance
      const newAnswered = new Map(answeredQuestions);
      newAnswered.set(activeQuestion.id, {
        text,
        parsed_intent: estimate.parsed_intent,
        confidence: estimate.confidence,
        defaulted: estimate.defaulted,
      });
      setAnsweredQuestions(newAnswered);
      setCurrentAnswerText("");
      advanceToNextUnanswered(newAnswered);
      announce(`Answer accepted with ${Math.round(estimate.confidence * 100)}% confidence. Moving to next question.`);
    } else {
      // Low confidence -- show follow-up
      setFollowUpActive(true);
      setFollowUpText("");
      // Store the initial answer temporarily
      setCurrentAnswerText(text);
      announce("Low confidence detected. Please clarify your answer.");
    }
  };

  const handleClarifySubmit = () => {
    if (!activeQuestion || !followUpText.trim()) return;

    const estimate = estimateConfidence(followUpText.trim());
    const newAnswered = new Map(answeredQuestions);
    newAnswered.set(activeQuestion.id, {
      text: followUpText.trim(),
      parsed_intent: estimate.parsed_intent,
      confidence: estimate.confidence,
      defaulted: estimate.defaulted,
    });
    setAnsweredQuestions(newAnswered);
    setFollowUpActive(false);
    setFollowUpText("");
    setCurrentAnswerText("");
    advanceToNextUnanswered(newAnswered);
    announce("Clarification accepted. Moving to next question.");
  };

  const handleSkip = () => {
    if (!activeQuestion) return;

    const newAnswered = new Map(answeredQuestions);
    newAnswered.set(activeQuestion.id, {
      text: "skip",
      parsed_intent: "DEFAULT",
      confidence: 0.0,
      defaulted: true,
    });
    setAnsweredQuestions(newAnswered);
    setFollowUpActive(false);
    setCurrentAnswerText("");
    advanceToNextUnanswered(newAnswered);
    announce("Question skipped with default answer. Moving to next question.");
  };

  const advanceToNextUnanswered = (answered: Map<string, ParsedAnswerLocal>) => {
    // Find next unanswered question after current index
    for (let i = activeQuestionIndex + 1; i < questions.length; i++) {
      if (!answered.has(questions[i].id)) {
        setActiveQuestionIndex(i);
        return;
      }
    }
    // Check before current index
    for (let i = 0; i < activeQuestionIndex; i++) {
      if (!answered.has(questions[i].id)) {
        setActiveQuestionIndex(i);
        return;
      }
    }
    // All answered -- keep index at end to show no active card
    setActiveQuestionIndex(questions.length);
  };

  const handleEdit = async (questionIndex: number) => {
    if (!deckId) return;

    // Capture from current state FIRST, before any async work
    const question = questions[questionIndex];
    const previousAnswer = answeredQuestions.get(question.id);

    // Fetch fresh session to avoid 409 on resubmission
    try {
      const freshData = await apiFetch<QuestionsListResponse>(
        `/api/v1/decks/${deckId}/questions`
      );
      setSessionId(freshData.session_id);
      setQuestions(freshData.questions);
    } catch (e) {
      // If we can't get a fresh session, continue with existing one
      // The user can still edit locally, just the final submit might need retry
    }

    const newAnswered = new Map(answeredQuestions);
    newAnswered.delete(question.id);
    setAnsweredQuestions(newAnswered);
    setActiveQuestionIndex(questionIndex);
    setCurrentAnswerText(previousAnswer?.text || "");
    setFollowUpActive(false);
    announce(`Editing answer for: ${question.template}`);
  };

  const handleGenerateNarratives = async () => {
    if (!deckId || !canGenerate || submitting) return;

    setSubmitting(true);
    setSubmitError(null);

    try {
      // Batch submit all answers -- auto-skip unanswered Tier 2+ questions
      const answers = questions.map((q) => {
        const localAnswer = answeredQuestions.get(q.id);
        return {
          question_id: q.id,
          text: localAnswer?.text || "skip",
        };
      });

      const response = await apiFetch<AnswerSubmitResponse>(
        `/api/v1/decks/${deckId}/answer-questions`,
        {
          method: "POST",
          body: JSON.stringify({
            session_id: sessionId,
            answers,
          }),
        }
      );

      if (response.ready_to_generate) {
        setSubmitting(false);
        navigate(`/decks/${deckId}/narratives`);
      } else {
        setSubmitError("Not all required questions have been answered. Please review Tier 1 questions.");
        setSubmitting(false);
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        // Answers already submitted for this session -- try getting a fresh session
        try {
          const freshData = await apiFetch<QuestionsListResponse>(
            `/api/v1/decks/${deckId}/questions`
          );
          setSessionId(freshData.session_id);
          // Retry with the fresh session -- auto-skip unanswered Tier 2+ questions
          const answers = questions.map((q) => {
            const localAnswer = answeredQuestions.get(q.id);
            return {
              question_id: q.id,
              text: localAnswer?.text || "skip",
            };
          });
          const retryResponse = await apiFetch<AnswerSubmitResponse>(
            `/api/v1/decks/${deckId}/answer-questions`,
            {
              method: "POST",
              body: JSON.stringify({
                session_id: freshData.session_id,
                answers,
              }),
            }
          );
          if (retryResponse.ready_to_generate) {
            setSubmitting(false);
            navigate(`/decks/${deckId}/narratives`);
          } else {
            setSubmitError("Not all required questions have been answered.");
            setSubmitting(false);
          }
        } catch (retryErr) {
          setSubmitError(
            retryErr instanceof ApiError ? retryErr.message : "Failed to submit answers. Please try again."
          );
          setSubmitting(false);
        }
      } else {
        setSubmitError(e instanceof ApiError ? e.message : "Failed to submit answers. Please try again.");
        setSubmitting(false);
      }
    }
  };

  /* ---- Follow-up prompt text ---- */

  const getFollowUpPrompt = () => {
    if (!activeQuestion) return "";
    const chips = activeQuestion.suggestion_chips;
    if (chips.length >= 2) {
      return `I'm not sure I understood -- did you mean "${chips[0]}" or "${chips[1]}"?`;
    }
    return "I'm not sure I understood -- did you mean one of the suggested options?";
  };

  /* ---- Render ---- */

  if (loading) {
    return (
      <AppShell steps={pipelineSteps()}>
        <p style={{ color: "#6b7280" }}>Loading questions...</p>
      </AppShell>
    );
  }

  if (error && !ingestData) {
    return (
      <AppShell steps={pipelineSteps()}>
        <div style={{ padding: 24, background: "#fef2f2", borderRadius: 8, color: "#991b1b" }}>
          {error}
          {error.includes("validation") && (
            <p style={{ marginTop: 12 }}>
              <a
                href={`/decks/${deckId}/validate`}
                style={{ color: "#2563eb", textDecoration: "underline" }}
              >
                Return to Validation Review
              </a>
            </p>
          )}
        </div>
      </AppShell>
    );
  }

  if (!ingestData) return null;

  if (questions.length === 0) {
    return (
      <AppShell steps={pipelineSteps()}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 8 }}>
          Clarifying Questions
        </h1>
        <p style={{ fontSize: 14, color: "#6b7280", marginBottom: 24 }}>
          No questions were generated for this dataset. You may proceed directly to narrative generation.
        </p>
        <button
          type="button"
          onClick={() => navigate(`/decks/${deckId}/narratives`)}
          style={{
            padding: "12px 28px",
            fontSize: 16,
            fontWeight: 700,
            color: "#fff",
            background: "#2563eb",
            border: "none",
            borderRadius: 8,
            cursor: "pointer",
          }}
        >
          Generate Narratives
        </button>
      </AppShell>
    );
  }

  // Derive context strip values
  const fileName = "Uploaded Data"; // ingest-status doesn't expose filename; use fallback
  const rowCount = ingestData.schema?.row_count ?? 0;
  const columnCount = ingestData.schema?.columns.length ?? 0;
  const issuesCount = ingestData.quality_report?.issues?.length ?? 0;

  // Split questions into answered (above) and active/remaining
  const answeredAbove = questions
    .slice(0, activeQuestionIndex)
    .filter((q) => answeredQuestions.has(q.id));
  const answeredBelow = questions
    .slice(activeQuestionIndex + 1)
    .filter((q) => answeredQuestions.has(q.id));

  return (
    <AppShell steps={pipelineSteps()}>
      {/* Aria live region for announcements */}
      <div
        ref={liveRegionRef}
        aria-live="polite"
        aria-atomic="true"
        style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0,0,0,0)" }}
      />

      <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 8 }}>
        Clarifying Questions
      </h1>
      <p style={{ fontSize: 14, color: "#6b7280", marginBottom: 24 }}>
        Answer the questions below to help the system generate better narratives.
        {questions.length > 0 && (
          <span>
            {" "}({answeredQuestions.size} of {questions.length} answered)
          </span>
        )}
      </p>

      {/* Data context strip */}
      <DataContextStrip
        fileName={fileName}
        rowCount={rowCount}
        columnCount={columnCount}
        issuesCount={issuesCount}
      />

      {/* Answered cards above active */}
      {answeredAbove.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
          {answeredAbove.map((q) => {
            const qIndex = questions.indexOf(q);
            return (
              <AnsweredCard
                key={q.id}
                question={q}
                answer={answeredQuestions.get(q.id)!}
                onEdit={() => handleEdit(qIndex)}
              />
            );
          })}
        </div>
      )}

      {/* Active question card */}
      {activeQuestion && !answeredQuestions.has(activeQuestion.id) && (
        <div style={{ marginBottom: 16 }}>
          <QuestionCard
            question={activeQuestion}
            onSubmit={handleSubmitAnswer}
            onSkip={handleSkip}
            initialValue={currentAnswerText || undefined}
            value={currentAnswerText}
            onChange={setCurrentAnswerText}
          />

          {/* Low-confidence follow-up */}
          {followUpActive && (
            <div
              style={{
                marginTop: 12,
                padding: 16,
                borderLeft: "4px solid #d97706",
                background: "#fffbeb",
                borderRadius: "0 6px 6px 0",
              }}
            >
              <p style={{ fontSize: 14, color: "#92400e", margin: "0 0 12px 0", fontWeight: 500 }}>
                {getFollowUpPrompt()}
              </p>
              <textarea
                value={followUpText}
                onChange={(e) => setFollowUpText(e.target.value)}
                placeholder="Clarify your answer..."
                aria-label="Clarify your answer"
                autoFocus
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
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    if (followUpText.trim()) handleClarifySubmit();
                  }
                }}
              />
              <button
                type="button"
                onClick={handleClarifySubmit}
                disabled={!followUpText.trim()}
                style={{
                  marginTop: 8,
                  padding: "8px 20px",
                  fontSize: 14,
                  fontWeight: 600,
                  color: "#fff",
                  background: followUpText.trim() ? "#d97706" : "#d1d5db",
                  border: "none",
                  borderRadius: 6,
                  cursor: followUpText.trim() ? "pointer" : "not-allowed",
                }}
              >
                Clarify
              </button>
            </div>
          )}
        </div>
      )}

      {/* Answered cards below active */}
      {answeredBelow.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
          {answeredBelow.map((q) => {
            const qIndex = questions.indexOf(q);
            return (
              <AnsweredCard
                key={q.id}
                question={q}
                answer={answeredQuestions.get(q.id)!}
                onEdit={() => handleEdit(qIndex)}
              />
            );
          })}
        </div>
      )}

      {/* Error banner */}
      {submitError && (
        <div
          style={{
            padding: "12px 16px",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 8,
            color: "#991b1b",
            fontSize: 14,
            marginBottom: 16,
          }}
        >
          {submitError}
        </div>
      )}

      {/* Generate Narratives button */}
      <div style={{ marginTop: 24 }}>
        <button
          type="button"
          onClick={handleGenerateNarratives}
          disabled={!canGenerate || submitting}
          style={{
            padding: "12px 28px",
            fontSize: 16,
            fontWeight: 700,
            color: "#fff",
            background: canGenerate && !submitting ? "#2563eb" : "#d1d5db",
            border: "none",
            borderRadius: 8,
            cursor: canGenerate && !submitting ? "pointer" : "not-allowed",
            position: "relative",
          }}
        >
          {submitting ? "Analyzing data and generating narrative options..." : "Generate Narratives"}
        </button>
        {canGenerate && !allQuestionsHandled && (
          <p style={{ fontSize: 13, color: "#6b7280", marginTop: 8 }}>
            Some optional questions are unanswered and will use default values.
          </p>
        )}
      </div>
    </AppShell>
  );
}
