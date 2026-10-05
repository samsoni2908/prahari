export interface WellbeingAssessment {
  id?: string;
  check_date: string;
  overall_score: number;
  sleep_score: number;
  workload_score: number;
  morale_score: number;
  answers_json?: Record<string, any>;
}

export interface SupportRequest {
  id: string;
  request_type: string;
  status: "SUBMITTED" | "IN_REVIEW" | "RESOLVED";
  urgency: "LOW" | "NORMAL" | "HIGH";
  created_at: string;
  resolved_at?: string;
}
