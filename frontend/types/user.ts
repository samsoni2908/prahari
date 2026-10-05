export type UserRole = "PERSONNEL" | "COMMANDER" | "WELFARE_OFFICER" | "ADMIN";

export interface User {
  id: string;
  username: string;
  role: UserRole;
  personnel_id?: string | null;
  unit_id?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}
