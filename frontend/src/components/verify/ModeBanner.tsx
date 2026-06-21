type ModeBannerProps = {
  passed: boolean;
  failCount: number;
  totalChecks: number;
  mode: "blocking" | "readonly";
  verifiedAt?: string;
};

export default function ModeBanner({ passed, failCount, totalChecks, mode, verifiedAt }: ModeBannerProps) {
  if (mode === "readonly") {
    return (
      <div
        role="status"
        aria-live="polite"
        style={{
          padding: "12px 24px",
          background: "#f0fdf4",
          color: "#166534",
          fontWeight: 600,
          fontSize: 16,
          borderRadius: 8,
          marginBottom: 16,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span aria-hidden="true">✓</span>
        <span>Verified {verifiedAt} · All checks pass</span>
      </div>
    );
  }

  const bg = passed ? "#f0fdf4" : "#fef2f2";
  const color = passed ? "#166534" : "#991b1b";
  const icon = passed ? "✓" : "✗";
  const text = passed
    ? "ALL CHECKS PASSED"
    : `${failCount} OF ${totalChecks} CHECKS FAILED — FIX REQUIRED`;

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        padding: "12px 24px",
        background: bg,
        color,
        fontWeight: 700,
        fontSize: 16,
        borderRadius: 8,
        marginBottom: 16,
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}
    >
      <span aria-hidden="true">{icon}</span>
      <span>{text}</span>
    </div>
  );
}
