type ModeBannerProps = {
  passed: boolean;
  failCount: number;
  totalChecks: number;
  unsignedAssumptionCount?: number;
  mode: "blocking" | "readonly";
  verifiedAt?: string;
};

export default function ModeBanner({ passed, failCount, totalChecks, unsignedAssumptionCount = 0, mode, verifiedAt }: ModeBannerProps) {
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

  const allClear = passed && unsignedAssumptionCount === 0;
  const bg = allClear ? "#f0fdf4" : "#fef2f2";
  const color = allClear ? "#166534" : "#991b1b";
  const icon = allClear ? "✓" : "✗";

  let text: string;
  if (allClear) {
    text = "ALL CHECKS PASSED";
  } else {
    const parts: string[] = [];
    if (failCount > 0) parts.push(`${failCount} of ${totalChecks} checks failed`);
    if (unsignedAssumptionCount > 0) parts.push(`${unsignedAssumptionCount} assumption${unsignedAssumptionCount !== 1 ? "s" : ""} need review`);
    text = parts.join(" · ").toUpperCase() + " — ACTION REQUIRED";
  }

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
