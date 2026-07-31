import { apiRequest, clearSession, getUser, setSession } from './api.js';

export async function login(email, password) {
  const payload = await apiRequest('/accounts/auth/login/', {
    method: 'POST',
    body: { email, password },
    auth: false,
  });

  setSession(payload);
  return payload.user;
}

export function logout() {
  clearSession();
  window.location.href = '/login.html';
}

export function routeByRole(user) {
  if (!user || !user.role) {
    window.location.href = '/login.html';
    return;
  }

  if (user.role === 'ADMIN') {
    window.location.href = '/admin/index.html';
    return;
  }

  if (user.role === 'REPORTER') {
    window.location.href = '/reports/index.html';
    return;
  }

  window.location.href = '/facility/index.html';
}

export function requireRole(allowedRoles) {
  const user = getUser();
  if (!user || !allowedRoles.includes(user.role)) {
    routeByRole(user);
    return null;
  }
  return user;
}
