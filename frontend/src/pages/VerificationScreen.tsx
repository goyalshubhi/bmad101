import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import AppShell from "../layouts/AppShell";
import ModeBanner from "../components/verify/ModeBanner";
import TabBar from "../components/verify/TabBar";
import FiguresTable from "../components/verify/FiguresTable";
import SourceRowsPanel from "../components/verify/SourceRowsPanel";
import ChecksList from "../components/verify/ChecksList";
import GateStatusBar from "../components/verify/GateStatusBar";
import DismissModal from "../components/verify/DismissModal";
import AssumptionsList from "../components/verify/AssumptionsList";
import { apiFetch, ApiError, BASE_URL } from "../api/client";
import type { VerifyResponse, FigureTrace, SourceRowsResponse } from "../types/verify";
import { buildPipelineSteps } from "../constants/pipelineSteps";

export default function VerificationScreen() {
  const { deckId } = useParams<{ deckId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const isReadonly = searchParams.get("mode") === "readonly";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifyResponse, setVerifyResponse] = useState<VerifyResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"figures" | "checks" | "assumptions">("figures");
  const [sourcePanel, setSourcePanel] = useState<{ figure: FigureTrace; data: SourceRowsResponse } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [dismissingCheck, setDismissingCheck] = useState<string | null>(null);
  const [dismissSubmitting, setDismissSubmitting] = useState(false);

  const liveRegionRef = useRef<HTMLDivElement>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  const announce = (message: string) => {
    if (liveRegionRef.current) {
      liveRegionRef.current.textContent = message;
    }
  };

  useEffect(() => {
    if (!deckId) return;
    let cancelled = false;

    setLoading(true);
    setError(null);
    setVerifyResponse(null);

    if (!isReadonly) {
      announce("Running reconciliation checks...");
    } else {
      announce("Loading verification results...");
    }

    (async () => {
      try {
        let result: VerifyResponse;
        if (isReadonly) {
          result = await apiFetch<VerifyResponse>(`/api/v1/decks/${deckId}/verify`);
        } else {
          try {
            result = await apiFetch<VerifyResponse>(`/api/v1/decks/${deckId}/verify`);
          } catch {
            result = await apiFetch<VerifyResponse>(`/api/v1/decks/${deckId}/verify`, {
              method: "POST",
            });
          }
        }
        if (cancelled) return;
        setVerifyResponse(result);
        if (!isReadonly) {
          announce(
            result.passed
              ? "All checks passed."
              : `${Object.values(result.checks).filter((c) => c.status === "fail").length} checks failed.`,
          );
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : "Failed to run verification");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [deckId, isReadonly]);

  const showToast = (msg: string) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToastMessage(msg);
    toastTimerRef.current = setTimeout(() => setToastMessage(null), 3000);
  };

  const handleVerifyUpdate = (newResponse: VerifyResponse) => {
    setVerifyResponse(newResponse);
    const failCount = Object.values(newResponse.checks).filter((c) => c.status === "fail").length;

    const aMap = new Map<number, string>();
    for (const a of newResponse.assumption_actions || []) {
      aMap.set(a.assumption_index, a.action);
    }
    const unsignedCount = (newResponse.assumptions || []).filter((a, i) => {
      if (a.flag_type !== "PATTERN" && a.flag_type !== "INFERRED") return false;
      const act = aMap.get(i);
      return act !== "acknowledged" && act !== "signed_off" && act !== "rejected";
    }).length;

    const totalBlockers = failCount + unsignedCount;
    if (totalBlockers === 0) {
      announce("All blockers resolved. You can proceed to render.");
    } else {
      const parts: string[] = [];
      if (failCount > 0) parts.push(`${failCount} check${failCount !== 1 ? "s" : ""} failing`);
      if (unsignedCount > 0) parts.push(`${unsignedCount} assumption${unsignedCount !== 1 ? "s" : ""} unsigned`);
      announce(parts.join(", ") + ".");
    }
  };

  const handleViewSource = async (figure: FigureTrace, index: number) => {
    if (!deckId || submitting) return;
    setSubmitting(true);
    try {
      const data = await apiFetch<SourceRowsResponse>(
        `/api/v1/decks/${deckId}/verify/source-rows?figure_index=${index}`,
      );
      setSourcePanel({ figure, data });
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "Failed to load source rows");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditNarrative = () => {
    if (deckId) {
      navigate(`/decks/${deckId}/narratives`);
    }
  };

  const handleApplyFix = async (checkName: string) => {
    if (!deckId || !verifyResponse) return;
    const check = verifyResponse.checks[checkName];
    if (!check?.fix_suggestion) {
      showToast("No automatic fix available for this check. Edit the narrative or exclude rows manually.");
      return;
    }
    try {
      const result = await apiFetch<VerifyResponse>(`/api/v1/decks/${deckId}/verify/apply-fix`, {
        method: "POST",
        body: JSON.stringify({
          report_id: verifyResponse.report_id,
          check_name: checkName,
          fix_type: "recalculate",
          parameters: { row_ids: [] },
        }),
      });
      handleVerifyUpdate(result);
    } catch (e) {
      throw e instanceof ApiError ? new Error(e.message) : e;
    }
  };

  const handleDismiss = (checkName: string) => {
    setDismissingCheck(checkName);
  };

  const handleDismissConfirm = async (reason: string) => {
    if (!deckId || !verifyResponse || !dismissingCheck || dismissSubmitting) return;
    setDismissSubmitting(true);
    try {
      const result = await apiFetch<VerifyResponse>(`/api/v1/decks/${deckId}/verify/dismiss-check`, {
        method: "POST",
        body: JSON.stringify({
          report_id: verifyResponse.report_id,
          check_name: dismissingCheck,
          reason,
        }),
      });
      handleVerifyUpdate(result);
      setDismissingCheck(null);
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "Failed to dismiss check");
    } finally {
      setDismissSubmitting(false);
    }
  };

  const handleAssumptionAction = async (index: number, action: string) => {
    if (!deckId || !verifyResponse) return;
    const result = await apiFetch<VerifyResponse>(`/api/v1/decks/${deckId}/verify/assumption-action`, {
      method: "POST",
      body: JSON.stringify({
        report_id: verifyResponse.report_id,
        assumption_index: index,
        action,
      }),
    });
    handleVerifyUpdate(result);
  };

  const handleAcknowledge = async (index: number) => {
    try {
      await handleAssumptionAction(index, "acknowledged");
    } catch (e) {
      throw e instanceof ApiError ? new Error(e.message) : e;
    }
  };

  const handleSignOff = async (index: number) => {
    try {
      await handleAssumptionAction(index, "signed_off");
    } catch (e) {
      throw e instanceof ApiError ? new Error(e.message) : e;
    }
  };

  const [challengeSubmitting, setChallengeSubmitting] = useState(false);

  const handleChallenge = (index: number) => {
    if (!deckId || !verifyResponse || challengeSubmitting) return;
    if (!window.confirm("This will navigate to the narrative editor. Unsaved verification changes may be lost. Continue?")) return;
    setChallengeSubmitting(true);
    handleAssumptionAction(index, "rejected")
      .then(() => navigate(`/decks/${deckId}/narratives?highlight=assumption-${index}`))
      .catch((e) => showToast(e instanceof ApiError ? e.message : "Failed to record challenge"))
      .finally(() => setChallengeSubmitting(false));
  };

  const handleReject = async (index: number) => {
    if (!deckId || !verifyResponse) return;
    if (!window.confirm("This will navigate to the narrative editor. Unsaved verification changes may be lost. Continue?")) return;
    try {
      await handleAssumptionAction(index, "rejected");
      navigate(`/decks/${deckId}/narratives?highlight=assumption-${index}`);
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "Failed to reject assumption");
    }
  };

  const handleProceedToRender = async () => {
    if (!deckId) return;
    try {
      await apiFetch(`/api/v1/decks/${deckId}/verify/complete`, { method: "POST" });
      navigate(`/decks/${deckId}/render`);
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "Failed to complete verification");
    }
  };

  const handleDownloadPptx = () => {
    if (!deckId) return;
    const link = document.createElement("a");
    link.href = `${BASE_URL}/api/v1/decks/${deckId}/render/download`;
    link.download = "deck.pptx";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleBackToNarrative = () => {
    if (deckId) {
      navigate(`/decks/${deckId}/narratives`);
    }
  };

  if (loading) {
    return (
      <AppShell steps={buildPipelineSteps(3)}>
        <div
          ref={liveRegionRef}
          aria-live="polite"
          aria-atomic="true"
          style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0,0,0,0)" }}
        />
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 8 }}>
          Verification
        </h1>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: 64,
            gap: 16,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              border: "4px solid #e5e7eb",
              borderTopColor: "#2563eb",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
            }}
          />
          <p style={{ fontSize: 16, color: "#374151", fontWeight: 500 }}>
            Running reconciliation checks...
          </p>
          <p style={{ fontSize: 13, color: "#6b7280" }}>
            This may take a few moments
          </p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell steps={buildPipelineSteps(3)}>
        <div style={{ padding: 24, background: "#fef2f2", borderRadius: 8, color: "#991b1b" }}>
          {error}
        </div>
      </AppShell>
    );
  }

  if (!verifyResponse) return null;

  const failedCheckCount = Object.values(verifyResponse.checks).filter((c) => c.status === "fail").length;
  const passedCheckCount = Object.values(verifyResponse.checks).filter((c) => c.status === "pass").length;
  const figurePassCount = verifyResponse.figure_traces.filter((f) => f.match_status !== "mismatch").length;
  const figureFailCount = verifyResponse.figure_traces.filter((f) => f.match_status === "mismatch").length;

  const actionMap = new Map<number, string>();
  for (const a of verifyResponse.assumption_actions || []) {
    actionMap.set(a.assumption_index, a.action);
  }
  const unsignedAssumptionCount = (verifyResponse.assumptions || []).filter((a, i) => {
    if (a.flag_type !== "PATTERN" && a.flag_type !== "INFERRED") return false;
    const act = actionMap.get(i);
    return act !== "acknowledged" && act !== "signed_off" && act !== "rejected";
  }).length;

  return (
    <AppShell steps={buildPipelineSteps(3)}>
      <div
        ref={liveRegionRef}
        aria-live="polite"
        aria-atomic="true"
        style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0,0,0,0)" }}
      />

      {toastMessage && (
        <div
          role="alert"
          style={{
            position: "fixed",
            top: 16,
            right: 16,
            padding: "12px 20px",
            background: "#374151",
            color: "#fff",
            borderRadius: 8,
            fontSize: 14,
            zIndex: 2000,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
          }}
        >
          {toastMessage}
        </div>
      )}

      {dismissingCheck && (
        <DismissModal
          checkName={dismissingCheck}
          onConfirm={handleDismissConfirm}
          onCancel={() => setDismissingCheck(null)}
        />
      )}

      <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 8 }}>
        Verification
      </h1>
      <p style={{ fontSize: 14, color: "#6b7280", marginBottom: 16 }}>
        Review reconciliation results and resolve any issues before proceeding.
      </p>

      <ModeBanner
        passed={verifyResponse.passed}
        failCount={failedCheckCount}
        totalChecks={Object.keys(verifyResponse.checks).length}
        unsignedAssumptionCount={unsignedAssumptionCount}
        mode={isReadonly ? "readonly" : "blocking"}
        verifiedAt={isReadonly && verifyResponse.verified_at ? new Date(verifyResponse.verified_at).toLocaleString() : undefined}
      />

      <TabBar
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab as "figures" | "checks" | "assumptions")}
        figureCounts={{
          total: verifyResponse.figure_traces.length,
          pass: figurePassCount,
          fail: figureFailCount,
        }}
        checkCounts={{
          pass: passedCheckCount,
          fail: failedCheckCount,
        }}
        unsignedAssumptionCount={unsignedAssumptionCount}
      />

      <div
        id="tabpanel-figures"
        role="tabpanel"
        aria-labelledby="tab-figures"
        hidden={activeTab !== "figures"}
      >
        {activeTab === "figures" && (
          <FiguresTable
            figureTraces={verifyResponse.figure_traces}
            onViewSource={handleViewSource}
            onEditNarrative={handleEditNarrative}
          />
        )}
      </div>

      <div
        id="tabpanel-checks"
        role="tabpanel"
        aria-labelledby="tab-checks"
        hidden={activeTab !== "checks"}
      >
        {activeTab === "checks" && (
          <ChecksList
            checks={verifyResponse.checks}
            onApplyFix={handleApplyFix}
            onDismiss={handleDismiss}
            onEditNarrative={handleEditNarrative}
          />
        )}
      </div>

      <div
        id="tabpanel-assumptions"
        role="tabpanel"
        aria-labelledby="tab-assumptions"
        hidden={activeTab !== "assumptions"}
      >
        {activeTab === "assumptions" && (
          <AssumptionsList
            assumptions={verifyResponse.assumptions || []}
            assumptionActions={verifyResponse.assumption_actions || []}
            onAcknowledge={handleAcknowledge}
            onSignOff={handleSignOff}
            onChallenge={handleChallenge}
            onReject={handleReject}
            mode={isReadonly ? "readonly" : "blocking"}
          />
        )}
      </div>

      {sourcePanel && (
        <SourceRowsPanel
          figure={sourcePanel.figure}
          sourceData={sourcePanel.data}
          onClose={() => setSourcePanel(null)}
        />
      )}

      <div style={{ height: 64 }} />

      <GateStatusBar
        failedCheckCount={failedCheckCount}
        unsignedAssumptionCount={unsignedAssumptionCount}
        onProceedToRender={handleProceedToRender}
        onBackToNarrative={handleBackToNarrative}
        onDownloadPptx={isReadonly ? handleDownloadPptx : undefined}
        mode={isReadonly ? "readonly" : "blocking"}
      />
    </AppShell>
  );
}
