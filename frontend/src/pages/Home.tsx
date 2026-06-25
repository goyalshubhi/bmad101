import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../layouts/AppShell";
import { apiFetch, ApiError, BASE_URL } from "../api/client";
import { buildPipelineSteps } from "../constants/pipelineSteps";

export default function Home() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const uploadingRef = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const acceptedTypes = [".csv", ".xlsx", ".json"];

  const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100 MB

  const handleFileSelect = (selected: File | null) => {
    if (!selected) return;
    const ext = "." + selected.name.split(".").pop()?.toLowerCase();
    if (!acceptedTypes.includes(ext)) {
      setError(`Unsupported file type. Please upload: ${acceptedTypes.join(", ")}`);
      return;
    }
    if (selected.size > MAX_FILE_SIZE) {
      setError("File is too large. Maximum size is 100 MB.");
      return;
    }
    setFile(selected);
    setError(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    handleFileSelect(dropped);
  };

  const handleUpload = async () => {
    if (!file || uploading || uploadingRef.current) return;
    uploadingRef.current = true;
    setUploading(true);
    setError(null);

    try {
      const deckName = file.name.replace(/\.[^.]+$/, "");
      const deck = await apiFetch<{ id: string }>("/api/v1/decks", {
        method: "POST",
        body: JSON.stringify({ name: deckName }),
      });

      const formData = new FormData();
      formData.append("file", file);

      const resp = await fetch(`${BASE_URL}/api/v1/decks/${deck.id}/ingest`, {
        method: "POST",
        body: formData,
      });

      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new ApiError(resp.status, body.detail || resp.statusText);
      }

      navigate(`/decks/${deck.id}/validate`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed. Please try again.");
      uploadingRef.current = false;
      setUploading(false);
    }
  };

  return (
    <AppShell steps={buildPipelineSteps(0)}>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 8 }}>
        Deck Generation System
      </h1>
      <p style={{ color: "#6b7280", marginBottom: 32 }}>
        Upload your data file to generate a boardroom-ready presentation deck.
      </p>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? "#2563eb" : "#d1d5db"}`,
          borderRadius: 12,
          padding: "48px 32px",
          textAlign: "center",
          cursor: "pointer",
          background: dragOver ? "#eff6ff" : file ? "#f0fdf4" : "#fafafa",
          transition: "all 0.15s",
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptedTypes.join(",")}
          onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
          style={{ display: "none" }}
        />

        {file ? (
          <>
            <div style={{ fontSize: 32, marginBottom: 8 }}>&#128196;</div>
            <p style={{ fontSize: 16, fontWeight: 600, color: "#111827" }}>{file.name}</p>
            <p style={{ fontSize: 13, color: "#6b7280", marginTop: 4 }}>
              {(file.size / 1024).toFixed(1)} KB — Click to change file
            </p>
          </>
        ) : (
          <>
            <div style={{ fontSize: 32, marginBottom: 8 }}>&#128228;</div>
            <p style={{ fontSize: 16, fontWeight: 600, color: "#374151" }}>
              Drop your file here or click to browse
            </p>
            <p style={{ fontSize: 13, color: "#9ca3af", marginTop: 4 }}>
              Supports {acceptedTypes.join(", ")} (max 100 MB)
            </p>
          </>
        )}
      </div>

      {error && (
        <div
          style={{
            marginTop: 16,
            padding: "12px 16px",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 8,
            color: "#991b1b",
            fontSize: 14,
          }}
        >
          {error}
        </div>
      )}

      <div style={{ marginTop: 24 }}>
        <button
          type="button"
          onClick={handleUpload}
          disabled={!file || uploading}
          style={{
            padding: "12px 28px",
            fontSize: 16,
            fontWeight: 700,
            color: "#fff",
            background: file && !uploading ? "#2563eb" : "#d1d5db",
            border: "none",
            borderRadius: 8,
            cursor: file && !uploading ? "pointer" : "not-allowed",
          }}
        >
          {uploading ? "Uploading & Analyzing..." : "Upload & Analyze"}
        </button>
      </div>
    </AppShell>
  );
}
