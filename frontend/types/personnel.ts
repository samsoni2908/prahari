export interface Personnel {
  id: string;
  personnel_code: string;
  pseudo_id: string;
  unit_id: string;
  rank_or_grade: string;
  role_title: string;
  status: string;
  joining_date?: string;
  service_years?: number;
}

export interface Deployment {
  id: string;
  personnel_id: string;
  location: string;
  terrain_type: string;
  start_date: string;
  end_date?: string;
  hardship_index?: number;
}

export interface DutyRecord {
  id: string;
  personnel_id: string;
  duty_type: string;
  duty_date: string;
  shift_hours: number;
  is_night_shift: boolean;
}

export interface LeaveRecord {
  id: string;
  personnel_id: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  status: string;
}
