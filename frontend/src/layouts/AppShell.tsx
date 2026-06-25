import ProgressRail from "../components/ProgressRail";
import { buildPipelineSteps } from "../constants/pipelineSteps";

const defaultSteps = buildPipelineSteps(-1);

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
