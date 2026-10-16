import { apiRequest, clearSession, getUser, setSession } from './api.js';

export async function login(email, password) {
  await apiRequest('/auth/csrf');
  const me = await apiRequest('/auth/login', {
    method: 'POST',
    body: { email, password },
  });

  const user = { ...me.legacy, email: me.email, first_name: me.first_name, last_name: me.last_name };
  setSession(user);
  return user;
}

export async function logout() {
  try {
    await apiRequest('/auth/logout', { method: 'POST' });
  } finally {
    clearSession();
    window.location.href = '/login.html';
  }
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
