export type PipelineStep = {
  label: string;
  status: "completed" | "active" | "inactive";
};

const STEP_LABELS = ["Upload", "Questions", "Story Options", "Verify", "Generate Deck"] as const;

export function buildPipelineSteps(activeIndex: number): PipelineStep[] {
  return STEP_LABELS.map((label, i) => ({
    label,
    status: i < activeIndex ? "completed" : i === activeIndex ? "active" : "inactive",
  }));
}
