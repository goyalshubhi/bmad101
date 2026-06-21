type DataContextStripProps = {
  fileName: string;
  rowCount: number;
  columnCount: number;
  issuesCount: number;
};

export default function DataContextStrip({
  fileName,
  rowCount,
  columnCount,
  issuesCount,
}: DataContextStripProps) {
  return (
    <div
      style={{
        background: "#f9fafb",
        borderBottom: "1px solid #e5e7eb",
        padding: "10px 16px",
        display: "flex",
        alignItems: "center",
        gap: 8,
        fontSize: 14,
        color: "#4b5563",
        marginBottom: 24,
        borderRadius: "6px 6px 0 0",
      }}
    >
      <span style={{ fontWeight: 600, color: "#111827" }}>{fileName}</span>
      <span style={{ color: "#9ca3af" }}>|</span>
      <span>{rowCount.toLocaleString()} rows</span>
      <span style={{ color: "#9ca3af" }}>|</span>
      <span>{columnCount} columns</span>
      <span style={{ color: "#9ca3af" }}>|</span>
      <span>
        {issuesCount} acknowledged issue{issuesCount !== 1 ? "s" : ""}
      </span>
    </div>
  );
}
