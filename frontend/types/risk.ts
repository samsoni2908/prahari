export type RiskBand = "LOW" | "MEDIUM" | "HIGH";

export interface RiskIndicator {
  personnel_id: string;
  wsi_score: number;
  risk_band: RiskBand;
  contributing_factors: Array<{ factor: string; impact: number }>;
  trend_direction: "UP" | "DOWN" | "STABLE";
  assessment_date: string;
}

export interface WSISnapshot {
  id: string;
  unit_id: string;
  snapshot_date: string;
  wsi_score: number;
  d_component: number;
  r_component: number;
  c_component: number;
  n_component: number;
  l_component: number;
  h_component: number;
  s_component: number;
}
