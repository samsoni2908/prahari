export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface WelfareRiskSummary {
  personnel_id: string;
  risk_score: number; // 0 - 100
  risk_level: RiskLevel;
  prediction_date: string;
  contributing_factors?: Array<string | { factor?: string; weight?: number; direction?: string; human_label?: string; [key: string]: any }>;
}
