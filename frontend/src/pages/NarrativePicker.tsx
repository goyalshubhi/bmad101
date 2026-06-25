import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppShell from "../layouts/AppShell";
import SkeletonCard from "../components/SkeletonCard";
import NarrativeCard from "../components/NarrativeCard";
import type { NarrativeData } from "../components/NarrativeCard";
import NarrativeDetailPanel from "../components/NarrativeDetailPanel";
import QASummaryBar from "../components/QASummaryBar";
import { apiFetch, ApiError } from "../api/client";
import { buildPipelineSteps } from "../constants/pipelineSteps";

type QASummaryItem = {
  id: string;
  template: string;
  answer: string;
  parsed_intent: string;
  confidence: number;
};

type NarrativesListResponse = {
  narratives: NarrativeData[];
};

type QASummaryResponse = {
  questions: QASummaryItem[];
};

type QuestionsListResponse = {
  session_id: string;
  questions: unknown[];
};


export default function NarrativePicker() {
  const { deckId } = useParams<{ deckId: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [narratives, setNarratives] = useState<NarrativeData[]>([]);
  const [qaItems, setQaItems] = useState<QASummaryItem[]>([]);

  const [selectedNarrativeId, setSelectedNarrativeId] = useState<string | null>(null);
  const [expandedNarrativeId, setExpandedNarrativeId] = useState<string | null>(null);
  const [editedTexts, setEditedTexts] = useState<Map<string, string>>(new Map());

  const [selecting, setSelecting] = useState(false);

  const liveRegionRef = useRef<HTMLDivElement>(null);
  const cardContainerRef = useRef<HTMLDivElement>(null);

  const announce = (message: string) => {
    if (liveRegionRef.current) {
      liveRegionRef.current.textContent = message;
    }
  };

  useEffect(() => {
    if (!deckId) return;
    let cancelled = false;

    (async () => {
      try {
        const [existingNarratives, qaSummary] = await Promise.all([
          apiFetch<NarrativesListResponse>(`/api/v1/decks/${deckId}/narratives`),
          apiFetch<QASummaryResponse>(`/api/v1/decks/${deckId}/qa-summary`),
        ]);

        if (cancelled) return;
        setQaItems(qaSummary.questions);

        if (existingNarratives.narratives.length > 0) {
          setNarratives(existingNarratives.narratives);
          setLoading(false);
          return;
        }

        const sessData = await apiFetch<QuestionsListResponse>(`/api/v1/decks/${deckId}/questions`);
        if (cancelled) return;

        const generated = await apiFetch<NarrativesListResponse>(
          `/api/v1/decks/${deckId}/generate-narratives`,
          {
            method: "POST",
            body: JSON.stringify({ session_id: sessData.session_id }),
          }
        );
        if (cancelled) return;

        setNarratives(generated.narratives);
        if (generated.narratives.length === 0) {
          setError("No narratives could be generated from the available data. Please go back and try different answers.");
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : "Failed to load narratives");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [deckId]);

  useEffect(() => {
    if (!loading && narratives.length > 0 && cardContainerRef.current) {
      const firstCard = cardContainerRef.current.querySelector<HTMLElement>("[role='button']");
      firstCard?.focus();
    }
  }, [loading, narratives.length]);

  const handleSelect = async (narrativeId: string) => {
    if (!deckId || selecting) return;
    setSelecting(true);

    try {
      await apiFetch(`/api/v1/decks/${deckId}/select-narrative`, {
        method: "POST",
        body: JSON.stringify({
          narrative_id: narrativeId,
          user_edits_text: editedTexts.get(narrativeId) || null,
        }),
      });
      setSelectedNarrativeId(narrativeId);
      announce("Narrative selected successfully.");
    } catch (e) {
      announce("Failed to select narrative.");
    } finally {
      setSelecting(false);
    }
  };

  const handleCardClick = (narrativeId: string) => {
    setExpandedNarrativeId(expandedNarrativeId === narrativeId ? null : narrativeId);
  };

  const handleEditSave = (narrativeId: string, text: string) => {
    const next = new Map(editedTexts);
    next.set(narrativeId, text);
    setEditedTexts(next);
    announce("Narrative edit saved.");
  };

  const handleVerifyProceed = () => {
    if (deckId && selectedNarrativeId) {
      navigate(`/decks/${deckId}/verify`);
    }
  };

  if (loading) {
    return (
      <AppShell steps={buildPipelineSteps(2)}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 8 }}>
          Narrative Options
        </h1>
        <p style={{ fontSize: 14, color: "#6b7280", marginBottom: 24 }}>
          Generating narrative options from your data...
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell steps={buildPipelineSteps(2)}>
        <div style={{ padding: 24, background: "#fef2f2", borderRadius: 8, color: "#991b1b" }}>
          {error}
        </div>
      </AppShell>
    );
  }

  if (narratives.length === 0) {
    return (
      <AppShell steps={buildPipelineSteps(2)}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 8 }}>
          Narrative Options
        </h1>
        <p style={{ fontSize: 14, color: "#6b7280" }}>
          No narratives were generated. Please go back and try different answers.
        </p>
      </AppShell>
    );
  }

  return (
    <AppShell steps={buildPipelineSteps(2)}>
      <div
        ref={liveRegionRef}
        aria-live="polite"
        aria-atomic="true"
        style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0,0,0,0)" }}
      />

      <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 8 }}>
        Narrative Options
      </h1>
      <p style={{ fontSize: 14, color: "#6b7280", marginBottom: 24 }}>
        Compare narrative angles and select the one that best tells your data story.
      </p>

      <QASummaryBar deckId={deckId!} questions={qaItems} />

      <div ref={cardContainerRef}>
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(narratives.length, 3)}, 1fr)`, gap: 16, marginBottom: expandedNarrativeId ? 0 : 24 }}>
          {narratives.map((n) => (
            <NarrativeCard
              key={n.id}
              narrative={n}
              isSelected={selectedNarrativeId === n.id}
              isExpanded={expandedNarrativeId === n.id}
              isModified={editedTexts.has(n.id)}
              onSelect={() => handleSelect(n.id)}
              onClick={() => handleCardClick(n.id)}
            />
          ))}
        </div>

        {expandedNarrativeId && (() => {
          const narrative = narratives.find((n) => n.id === expandedNarrativeId);
          if (!narrative) return null;
          return (
            <NarrativeDetailPanel
              key={expandedNarrativeId}
              narrative={narrative}
              editedText={editedTexts.get(expandedNarrativeId) ?? null}
              onSave={(text) => handleEditSave(expandedNarrativeId, text)}
              onClose={() => setExpandedNarrativeId(null)}
            />
          );
        })()}
      </div>

      <div style={{ marginTop: 24 }}>
        <button
          type="button"
          onClick={handleVerifyProceed}
          disabled={!selectedNarrativeId}
          style={{
            padding: "12px 28px", fontSize: 16, fontWeight: 700,
            color: "#fff",
            background: selectedNarrativeId ? "#2563eb" : "#d1d5db",
            border: "none", borderRadius: 8,
            cursor: selectedNarrativeId ? "pointer" : "not-allowed",
          }}
        >
          Verify & Proceed
        </button>
      </div>
    </AppShell>
  );
}
