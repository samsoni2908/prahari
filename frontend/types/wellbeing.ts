export interface WellbeingResult {
  id: string;
  personnel_id: string;
  instrument_name: string;
  assessment_date: string;
  category_label?: string;
  trend_label?: string;
  score_summary_json: Record<string, any>;
}
