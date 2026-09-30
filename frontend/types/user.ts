export interface User {
  id: string;
  username: string;
  role: 'PERSONNEL' | 'COMMANDER' | 'WELFARE_OFFICER' | 'ADMIN';
  personnel_id?: string;
  unit_id?: string;
  is_active: boolean;
  created_at: string;
}
