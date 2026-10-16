window.AFYASYNC_CONFIG = {
  // Same origin: nginx serves these pages and routes /api/ to Django (session cookie + CSRF).
  API_BASE_URL: '/api/v1',
  // Demo shortcuts fill the e-mail only; passwords are never shipped in the page.
  DEMO_LOGINS: [
    { label: 'Admin', email: 'admin@afyasync.dima.co.ke' },
    { label: 'Facility', email: 'facility@afyasync.dima.co.ke' },
    { label: 'Reporter', email: 'reporter@afyasync.dima.co.ke' },
  ],
};
