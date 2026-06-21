const shimmerKeyframes = `
@keyframes shimmer {
  0% { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}
`;

const shimmerStyle: React.CSSProperties = {
  background: "linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 50%, #f3f4f6 75%)",
  backgroundSize: "800px 100%",
  animation: "shimmer 1.5s infinite linear",
  borderRadius: 4,
};

export default function SkeletonCard() {
  return (
    <>
      <style>{shimmerKeyframes}</style>
      <div
        style={{
          width: "100%",
          height: 220,
          border: "1px solid #e5e7eb",
          borderRadius: 12,
          padding: 20,
          display: "flex",
          flexDirection: "column",
          gap: 12,
          background: "#fff",
        }}
        aria-hidden="true"
      >
        <div style={{ ...shimmerStyle, width: "60%", height: 20 }} />
        <div style={{ ...shimmerStyle, width: "100%", height: 40 }} />
        <div style={{ ...shimmerStyle, width: "40%", height: 16 }} />
        <div style={{ display: "flex", gap: 12 }}>
          <div style={{ ...shimmerStyle, width: 80, height: 24 }} />
          <div style={{ ...shimmerStyle, width: 80, height: 24 }} />
        </div>
        <div style={{ marginTop: "auto" }}>
          <div style={{ ...shimmerStyle, width: 100, height: 36 }} />
        </div>
      </div>
    </>
  );
}
