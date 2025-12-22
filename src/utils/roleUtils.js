export const ROLES = {
  ADMIN: 'Admin',
  MANAGER: 'Yönetici',
  DIRECTOR: 'Müdür',
  FIELD: 'Saha Personeli'
};

export const PERMISSIONS = {
  VIEW_REPORTS: [ROLES.ADMIN, ROLES.DIRECTOR],
  MANAGE_USERS: [ROLES.ADMIN],
  ASSIGN_JOBS: [ROLES.ADMIN, ROLES.MANAGER],
};
