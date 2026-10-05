// PRAHARI Role & Scope Permission Helpers

export type Role = "PERSONNEL" | "COMMANDER" | "WELFARE_OFFICER" | "ADMIN";

export function canAccessCommanderView(role: string): boolean {
  return role === "COMMANDER" || role === "ADMIN";
}

export function canAccessWelfareView(role: string): boolean {
  return role === "WELFARE_OFFICER";
}

export function canAccessAdminView(role: string): boolean {
  return role === "ADMIN";
}

export function canAccessPrivateWellbeing(role: string, targetUserId: string, currentUserId: string): boolean {
  // Only the personnel themselves can view raw wellbeing
  return role === "PERSONNEL" && targetUserId === currentUserId;
}
