import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppShell from "../layouts/AppShell";
import { apiFetch, ApiError } from "../api/client";

type QualityIssue = { severity: string; description: string; count: number; sample_rows?: number[] };

type SchemaColumn = { name: string; type: string; nullable_pct: number };

type IngestStatus = {
  ingest_job_id: string;
  schema: Record<string, { type: string; nullability?: number; cardinality?: number }> | null;
  quality_report: {
    status: string;
    quality_issues?: QualityIssue[];
    issues?: QualityIssue[];
  } | null;
  status: string;
  validated_at: string | null;
};

function getIssues(report: IngestStatus["quality_report"]): QualityIssue[] {
  if (!report) return [];
  return report.quality_issues ?? report.issues ?? [];
}

function getColumns(schema: IngestStatus["schema"]): SchemaColumn[] {
  if (!schema || Array.isArray(schema)) return [];
  return Object.entries(schema).map(([name, info]) => ({
    name,
    type: info.type ?? "unknown",
    nullable_pct: info.nullability ?? 0,
  }));
}

const pipelineSteps = (status: string) => [
  { label: "Ingest", status: (status === "CLEAN" || status === "ISSUES_ACKNOWLEDGED") ? "completed" as const : "active" as const },
  { label: "Questions", status: "inactive" as const },
  { label: "Narratives", status: "inactive" as const },
  { label: "Verify", status: "inactive" as const },
  { label: "Render", status: "inactive" as const },
];

const severityColor: Record<string, string> = {
  high: "#dc2626",
  medium: "#d97706",
  low: "#9ca3af",
};

export default function ValidationReview() {
  const { deckId } = useParams<{ deckId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<IngestStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [acknowledging, setAcknowledging] = useState(false);

  useEffect(() => {
    if (!deckId) return;
    let cancelled = false;
    (async () => {
      try {
        const result = await apiFetch<IngestStatus>(`/api/v1/decks/${deckId}/ingest-status`);
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : "Failed to load ingest status");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [deckId]);

  const refetchStatus = async () => {
    if (!deckId) return;
    try {
      const result = await apiFetch<IngestStatus>(`/api/v1/decks/${deckId}/ingest-status`);
      setData(result);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to reload status");
    }
  };

  const handleAcknowledge = async () => {
    if (!deckId) return;
    setAcknowledging(true);
    try {
      const tempUserId = "00000000-0000-0000-0000-000000000001";
      await apiFetch(`/api/v1/decks/${deckId}/validate-acknowledge`, {
        method: "POST",
        body: JSON.stringify({ user_id: tempUserId }),
      });
      await refetchStatus();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Network error. Please try again.");
    } finally {
      setAcknowledging(false);
    }
  };

  const canProceed = data?.status === "CLEAN" || data?.status === "ISSUES_ACKNOWLEDGED";

  if (loading) {
    return (
      <AppShell>
        <p style={{ color: "#6b7280" }}>Loading ingest status...</p>
      </AppShell>
    );
  }

  if (error && !data) {
    return (
      <AppShell>
        <div style={{ padding: 24, background: "#fef2f2", borderRadius: 8, color: "#991b1b" }}>
          {error}
        </div>
      </AppShell>
    );
  }

  if (!data) return null;

  return (
    <AppShell steps={pipelineSteps(data.status)}>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 24 }}>
        Data Validation Review
      </h1>

      {/* Status Banner */}
      <StatusBanner status={data.status} issueCount={getIssues(data.quality_report).length} />

      {/* Schema Summary */}
      {data.schema && (() => {
        const columns = getColumns(data.schema);
        return columns.length > 0 ? (
          <section style={{ marginTop: 24 }}>
            <h2 style={{ fontSize: 18, fontWeight: 600, color: "#111827", marginBottom: 12 }}>
              Schema Summary
            </h2>
            <p style={{ color: "#6b7280", marginBottom: 12 }}>
              {columns.length} columns detected
            </p>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
                  <th style={{ padding: "8px 12px", color: "#6b7280" }}>Column</th>
                  <th style={{ padding: "8px 12px", color: "#6b7280" }}>Type</th>
                  <th style={{ padding: "8px 12px", color: "#6b7280" }}>Nullable %</th>
                </tr>
              </thead>
              <tbody>
                {columns.map((col) => (
                  <tr key={col.name} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "8px 12px", fontWeight: 500 }}>{col.name}</td>
                    <td style={{ padding: "8px 12px", color: "#6b7280" }}>{col.type}</td>
                    <td style={{ padding: "8px 12px", color: "#6b7280" }}>{(col.nullable_pct * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ) : null;
      })()}

      {/* Quality Issues */}
      {(() => {
        const issues = getIssues(data.quality_report);
        return issues.length > 0 ? (
          <section style={{ marginTop: 24 }}>
            <h2 style={{ fontSize: 18, fontWeight: 600, color: "#111827", marginBottom: 12 }}>
              Quality Issues
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {issues.map((issue, i) => (
                <div
                  key={i}
                  style={{
                    padding: 16,
                    border: "1px solid #e5e7eb",
                    borderRadius: 8,
                    borderLeft: `4px solid ${severityColor[issue.severity] || "#9ca3af"}`,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span
                      style={{
                        fontSize: 12,
                        fontWeight: 600,
                        textTransform: "uppercase",
                        color: "#fff",
                        background: severityColor[issue.severity] || "#9ca3af",
                        padding: "2px 8px",
                        borderRadius: 4,
                      }}
                    >
                      {issue.severity}
                    </span>
                    <span style={{ fontSize: 14, color: "#6b7280" }}>
                      {issue.count} occurrence{issue.count !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <p style={{ fontSize: 14, color: "#111827", margin: 0 }}>{issue.description}</p>
                  {(issue.sample_rows?.length ?? 0) > 0 && (
                    <p style={{ fontSize: 12, color: "#9ca3af", margin: "4px 0 0" }}>
                      Sample rows: {issue.sample_rows!.join(", ")}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </section>
        ) : null;
      })()}

      {/* Action Buttons */}
      <div style={{ marginTop: 32, display: "flex", gap: 12 }}>
        {data.status === "ISSUES_BLOCKING" && (
          <button
            onClick={handleAcknowledge}
            disabled={acknowledging}
            style={{
              padding: "10px 20px",
              fontSize: 14,
              fontWeight: 600,
              color: "#fff",
              background: acknowledging ? "#9ca3af" : "#dc2626",
              border: "none",
              borderRadius: 6,
              cursor: acknowledging ? "not-allowed" : "pointer",
            }}
          >
            {acknowledging ? "Acknowledging..." : "Acknowledge All Issues"}
          </button>
        )}
        <button
          disabled={!canProceed}
          onClick={() => {
            if (canProceed && deckId) {
              navigate(`/decks/${deckId}/questions`);
            }
          }}
          style={{
            padding: "10px 20px",
            fontSize: 14,
            fontWeight: 600,
            color: "#fff",
            background: canProceed ? "#2563eb" : "#d1d5db",
            border: "none",
            borderRadius: 6,
            cursor: canProceed ? "pointer" : "not-allowed",
          }}
        >
          Proceed to Questions
        </button>
      </div>
    </AppShell>
  );
}

function StatusBanner({ status, issueCount }: { status: string; issueCount: number }) {
  const config: Record<string, { bg: string; border: string; color: string; text: string }> = {
    CLEAN: {
      bg: "#f0fdf4",
      border: "#bbf7d0",
      color: "#166534",
      text: "No Issues Found",
    },
    ISSUES_BLOCKING: {
      bg: "#fef2f2",
      border: "#fecaca",
      color: "#991b1b",
      text: `${issueCount} Issue${issueCount !== 1 ? "s" : ""} Require Acknowledgment`,
    },
    ISSUES_ACKNOWLEDGED: {
      bg: "#eff6ff",
      border: "#bfdbfe",
      color: "#1e40af",
      text: "Issues Acknowledged",
    },
  };

  const fallback = { bg: "#fefce8", border: "#fde68a", color: "#92400e", text: `Unknown Status: ${status}` };
  const c = config[status] || fallback;

  return (
    <div
      style={{
        padding: "12px 16px",
        background: c.bg,
        border: `1px solid ${c.border}`,
        borderRadius: 8,
        color: c.color,
        fontWeight: 600,
        fontSize: 14,
      }}
    >
      {c.text}
    </div>
  );
}
