// PRAHARI Client-side Auth & Session Utilities

export interface UserSession {
  user_id: string;
  username: string;
  role: "PERSONNEL" | "COMMANDER" | "WELFARE_OFFICER" | "ADMIN";
  personnel_id?: string;
  unit_id?: string;
}

export function getRoleDashboardPath(role: string): string {
  switch (role) {
    case "COMMANDER":
      return "/commander";
    case "WELFARE_OFFICER":
      return "/welfare";
    case "ADMIN":
      return "/admin";
    case "PERSONNEL":
    default:
      return "/personnel";
  }
}
