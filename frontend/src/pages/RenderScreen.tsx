import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppShell from "../layouts/AppShell";
import { apiFetch, ApiError } from "../api/client";

type RenderResponse = {
  deck_id: string;
  version: number;
  pptx_url: string;
  status: string;
};

const loadingSteps = () => [
  { label: "Ingest", status: "completed" as const },
  { label: "Questions", status: "completed" as const },
  { label: "Narratives", status: "completed" as const },
  { label: "Verify", status: "completed" as const },
  { label: "Render", status: "active" as const },
];

const doneSteps = () => [
  { label: "Ingest", status: "completed" as const },
  { label: "Questions", status: "completed" as const },
  { label: "Narratives", status: "completed" as const },
  { label: "Verify", status: "completed" as const },
  { label: "Render", status: "completed" as const },
];

export default function RenderScreen() {
  const { deckId } = useParams<{ deckId: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [renderResult, setRenderResult] = useState<RenderResponse | null>(null);
  const [downloading, setDownloading] = useState(false);

  const liveRegionRef = useRef<HTMLDivElement>(null);
  const renderFiredRef = useRef(false);

  const announce = (message: string) => {
    if (liveRegionRef.current) {
      liveRegionRef.current.textContent = message;
    }
  };

  useEffect(() => {
    if (!deckId || renderFiredRef.current) return;
    renderFiredRef.current = true;
    let cancelled = false;

    announce("Generating boardroom-ready deck...");

    (async () => {
      try {
        const result = await apiFetch<RenderResponse>(
          `/api/v1/decks/${deckId}/render`,
          { method: "POST" }
        );
        if (cancelled) return;
        setRenderResult(result);
        setLoading(false);
        announce("Your deck is ready for download!");
      } catch (e) {
        if (cancelled) return;
        setError(
          e instanceof ApiError ? e.message : "Failed to render deck"
        );
        setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [deckId]);

  const handleDownload = async () => {
    if (!deckId || downloading) return;
    setDownloading(true);
    try {
      const link = document.createElement("a");
      link.href = `/api/v1/decks/${deckId}/render/download`;
      link.download = `deck_v${renderResult?.version || 1}.pptx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } finally {
      setDownloading(false);
    }
  };

  const retryRef = useRef(false);

  const handleRetry = () => {
    if (!deckId || retryRef.current) return;
    retryRef.current = true;
    setLoading(true);
    setError(null);
    setRenderResult(null);
    let cancelled = false;
    announce("Retrying deck generation...");
    (async () => {
      try {
        const result = await apiFetch<RenderResponse>(
          `/api/v1/decks/${deckId}/render`,
          { method: "POST" }
        );
        if (cancelled) return;
        setRenderResult(result);
        setLoading(false);
        announce("Your deck is ready for download!");
      } catch (e) {
        if (cancelled) return;
        setError(
          e instanceof ApiError ? e.message : "Failed to render deck"
        );
        setLoading(false);
      } finally {
        retryRef.current = false;
      }
    })();
  };

  const steps = renderResult ? doneSteps() : loadingSteps();

  if (loading) {
    return (
      <AppShell steps={steps}>
        <div
          ref={liveRegionRef}
          aria-live="polite"
          aria-atomic="true"
          style={{
            position: "absolute",
            width: 1,
            height: 1,
            overflow: "hidden",
            clip: "rect(0,0,0,0)",
          }}
        />
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: 400,
            gap: 24,
          }}
        >
          <div
            style={{
              width: 48,
              height: 48,
              border: "4px solid #e5e7eb",
              borderTopColor: "#2563eb",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
            }}
          />
          <p style={{ fontSize: 18, color: "#1a1a2e", fontWeight: 600 }}>
            Generating boardroom-ready deck...
          </p>
          <p style={{ fontSize: 14, color: "#6b7280" }}>
            Building slides from your verified narrative
          </p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell steps={steps}>
        <div
          ref={liveRegionRef}
          aria-live="polite"
          aria-atomic="true"
          style={{
            position: "absolute",
            width: 1,
            height: 1,
            overflow: "hidden",
            clip: "rect(0,0,0,0)",
          }}
        />
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: 400,
            gap: 16,
          }}
        >
          <div
            style={{
              background: "#fef2f2",
              border: "1px solid #fecaca",
              borderRadius: 12,
              padding: "32px 48px",
              textAlign: "center",
              maxWidth: 500,
            }}
          >
            <p style={{ fontSize: 16, color: "#991b1b", fontWeight: 600, marginBottom: 12 }}>
              Rendering Failed
            </p>
            <p style={{ fontSize: 14, color: "#991b1b" }}>{error}</p>
            <button
              type="button"
              onClick={handleRetry}
              style={{
                marginTop: 20,
                padding: "10px 24px",
                fontSize: 14,
                fontWeight: 600,
                color: "#fff",
                background: "#2563eb",
                border: "none",
                borderRadius: 8,
                cursor: "pointer",
              }}
            >
              Retry
            </button>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell steps={steps}>
      <div
        ref={liveRegionRef}
        aria-live="polite"
        aria-atomic="true"
        style={{
          position: "absolute",
          width: 1,
          height: 1,
          overflow: "hidden",
          clip: "rect(0,0,0,0)",
        }}
      />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: 400,
          gap: 24,
        }}
      >
        <div
          style={{
            background: "#f0fdf4",
            border: "1px solid #bbf7d0",
            borderRadius: 16,
            padding: "48px 64px",
            textAlign: "center",
            maxWidth: 520,
          }}
        >
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: "50%",
              background: "#16a34a",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 20px",
              fontSize: 32,
              color: "#fff",
            }}
            aria-hidden="true"
          >
            ✓
          </div>
          <h2 style={{ fontSize: 24, color: "#1a1a2e", fontWeight: 700, marginBottom: 8 }}>
            Your deck is ready!
          </h2>
          <p style={{ fontSize: 14, color: "#6b7280", marginBottom: 24 }}>
            Version {renderResult?.version} generated successfully
          </p>

          <button
            type="button"
            onClick={handleDownload}
            disabled={downloading}
            aria-label="Download PPTX deck"
            style={{
              padding: "14px 36px",
              fontSize: 16,
              fontWeight: 700,
              color: "#fff",
              background: downloading ? "#9ca3af" : "#2563eb",
              border: "none",
              borderRadius: 8,
              cursor: downloading ? "not-allowed" : "pointer",
              marginBottom: 16,
            }}
          >
            {downloading ? "Downloading..." : "Download PPTX"}
          </button>

          <div>
            <button
              type="button"
              onClick={() => navigate(`/decks/${deckId}/verify?mode=readonly`)}
              style={{
                padding: "8px 16px",
                fontSize: 14,
                fontWeight: 500,
                color: "#2563eb",
                background: "none",
                border: "none",
                cursor: "pointer",
                textDecoration: "underline",
              }}
            >
              ← Back to Verification
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
