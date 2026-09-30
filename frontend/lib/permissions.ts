// Role verification & route authorization guards
export const ROLES = {
  PERSONNEL: 'PERSONNEL',
  COMMANDER: 'COMMANDER',
  WELFARE_OFFICER: 'WELFARE_OFFICER',
  ADMIN: 'ADMIN',
} as const;

export type UserRole = typeof ROLES[keyof typeof ROLES];
