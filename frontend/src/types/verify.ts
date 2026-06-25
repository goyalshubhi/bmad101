export type FigureTrace = {
  figure_value: string;
  source_rows: string;
  formula: string;
  match_status: "exact" | "within_tolerance" | "mismatch";
  variance_pct: number;
};

export type CheckResult = {
  status: "pass" | "fail" | "dismissed";
  expected?: unknown;
  actual?: unknown;
  fix_suggestion?: string | null;
  dismissed_reason?: string;
  dismissed_by?: string;
  dismissed_at?: string;
};

export type ApplyFixRequest = {
  report_id: string;
  check_name: string;
  fix_type: "exclude_rows" | "recalculate";
  parameters: { row_ids: number[] };
};

export type DismissCheckRequest = {
  report_id: string;
  check_name: string;
  reason: string;
};

export type AssumptionItem = {
  text: string;
  flag_type: "EXPLICIT" | "PATTERN" | "INFERRED";
  confidence: number;
  source_reference: string;
};

export type AssumptionAction = {
  assumption_index: number;
  action: "acknowledged" | "signed_off" | "rejected";
  user_id: string;
  created_at: string;
};

export type AssumptionActionRequest = {
  report_id: string;
  assumption_index: number;
  action: "acknowledged" | "signed_off" | "rejected";
};

export type VerifyResponse = {
  report_id: string;
  deck_id: string;
  narrative_id: string;
  passed: boolean;
  checks: Record<string, CheckResult>;
  figure_traces: FigureTrace[];
  assumptions: AssumptionItem[];
  assumption_actions: AssumptionAction[];
  verified_at: string | null;
};

export type SourceRowsResponse = {
  figure_value: string;
  formula: string;
  rows: Record<string, unknown>[];
};
