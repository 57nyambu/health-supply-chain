export function getApiBaseUrl() {
  const configured = window.AFYASYNC_CONFIG && window.AFYASYNC_CONFIG.API_BASE_URL;
  return configured || 'http://localhost:8000/api/v1';
}

export function getToken() {
  return sessionStorage.getItem('afyasync_access');
}

export function setSession(payload) {
  sessionStorage.setItem('afyasync_access', payload.access || '');
  sessionStorage.setItem('afyasync_refresh', payload.refresh || '');
  sessionStorage.setItem('afyasync_user', JSON.stringify(payload.user || {}));
}

export function clearSession() {
  sessionStorage.removeItem('afyasync_access');
  sessionStorage.removeItem('afyasync_refresh');
  sessionStorage.removeItem('afyasync_user');
}

export function getUser() {
  const raw = sessionStorage.getItem('afyasync_user');
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch (error) {
    return null;
  }
}

export async function apiRequest(path, options = {}) {
  const method = options.method || 'GET';
  const body = options.body;
  const isFormData = body instanceof FormData;

  const headers = {
    ...(options.headers || {}),
  };

  if (!isFormData && body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  if (options.auth !== false) {
    const token = getToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method,
    headers,
    body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let details = `HTTP ${response.status}`;
    try {
      const json = await response.json();
      details = json.error || json.detail || JSON.stringify(json);
    } catch (error) {
      details = response.statusText || details;
    }
    throw new Error(details);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
