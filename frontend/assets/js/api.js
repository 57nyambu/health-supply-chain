// Legacy dashboards (removed in P1-WEB-06). Same-origin session cookie + CSRF:
// no tokens are kept in browser storage (ADR-005).

export function getApiBaseUrl() {
  const configured = window.AFYASYNC_CONFIG && window.AFYASYNC_CONFIG.API_BASE_URL;
  return configured || '/api/v1';
}

export function setSession(user) {
  sessionStorage.setItem('afyasync_user', JSON.stringify(user || {}));
}

export function clearSession() {
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

function csrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
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

  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    headers['X-CSRFToken'] = csrfToken();
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method,
    headers,
    credentials: 'same-origin',
    body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let details = `HTTP ${response.status}`;
    try {
      const json = await response.json();
      details = json.detail || json.error || JSON.stringify(json);
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
