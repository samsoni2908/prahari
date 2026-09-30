// Frontend authentication helper functions
export interface CurrentUser {
  id: string;
  username: string;
  role: 'PERSONNEL' | 'COMMANDER' | 'WELFARE_OFFICER' | 'ADMIN';
  personnelId?: string;
  unitId?: string;
}
