export type QualityIssue = {
  severity: string;
  description: string;
  count: number;
  sample_rows?: number[];
};

export type IngestStatus = {
  ingest_job_id: string;
  schema: Record<string, { type: string; nullability?: number; cardinality?: number }> | null;
  quality_report: {
    status: string;
    quality_issues?: QualityIssue[];
    issues?: QualityIssue[];
  } | null;
  status: string;
  validated_at: string | null;
};
