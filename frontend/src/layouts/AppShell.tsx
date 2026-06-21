import ProgressRail from "../components/ProgressRail";

const defaultSteps = [
  { label: "Ingest", status: "inactive" as const },
  { label: "Questions", status: "inactive" as const },
  { label: "Narratives", status: "inactive" as const },
  { label: "Verify", status: "inactive" as const },
  { label: "Render", status: "inactive" as const },
];

type AppShellProps = {
  children?: React.ReactNode;
  steps?: { label: string; status: "completed" | "active" | "inactive" }[];
};

export default function AppShell({ children, steps }: AppShellProps) {
  return (
    <div style={{ display: "flex", minHeight: "100vh", minWidth: 1280 }}>
      <ProgressRail steps={steps || defaultSteps} />
      <main style={{ flex: 1, padding: 32 }}>
        {children}
      </main>
    </div>
  );
}
