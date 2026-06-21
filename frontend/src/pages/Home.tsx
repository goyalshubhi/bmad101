import AppShell from "../layouts/AppShell";

export default function Home() {
  return (
    <AppShell>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827" }}>
        Deck Generation System
      </h1>
      <p style={{ color: "#6b7280", marginTop: 8 }}>
        Upload data to get started.
      </p>
    </AppShell>
  );
}
