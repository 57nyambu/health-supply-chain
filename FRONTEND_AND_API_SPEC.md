# Frontend and API Specification
Smart Health Extension - Track 3 (Build with Gemma: GDG Pwani)
Working name: AfyaSync
Frontend host: https://afyasyc.dima.co.ke

## 0. Deployment shape

- Backend: Django + DRF + Celery, deployed as systemd services (gunicorn + celery worker + celery beat).
- Frontend: static vanilla HTML/CSS/JS in frontend/, served by nginx at https://afyasyc.dima.co.ke.
- API routing: nginx proxies /api/ to gunicorn socket.
- Notifications: email-only for this build. SMS code remains in place and can be re-enabled by setting NOTIFICATION_CHANNEL=sms.

## 1. Frontend structure

```
frontend/
  assets/
    css/
      tokens.css
      base.css
      components.css
    js/
      config.js
      api.js
      auth.js
      dashboard.js
  deploy/
    generate-frontend-config.sh
    generate-frontend-config.ps1
  login.html
  admin/index.html
  facility/index.html
  reports/index.html
  .env.example
```

## 2. Role dashboards

- Tier 1 (ADMIN): /admin/index.html
- Tier 2 (BRANCH_MANAGER, WAREHOUSE, PROCUREMENT, CASHIER): /facility/index.html
- Tier 3 internal (REPORTER): /reports/index.html

All dashboards share one style system and icon set (Bootstrap Icons via CDN).

## 3. Frontend AI integration

AI is integrated directly in frontend flows:

- Assistant chat (Tier 1 and Tier 2): POST /api/v1/ai/assistant/
- Forecast line per facility card (Tier 1 and Tier 2): GET /api/v1/ai/forecast/<warehouse_id>/<product_id>/
- OCR intake (Tier 1 and Tier 2): POST /api/v1/ai/ocr-intake/
- Redistribution suggestions (Tier 1 only): GET /api/v1/ai/redistribution-suggestions/

Reporter dashboard does not call any AI endpoint.

## 4. UAC and backend permissions

### 4.1 Tier model

- Tier 1: ADMIN
- Tier 2: BRANCH_MANAGER, WAREHOUSE, PROCUREMENT, CASHIER
- Tier 3 internal: REPORTER (read-only)
- Tier 3 external: API-key authenticated clients (X-API-Key) for public endpoints only

Tier-2 warehouse scoping is resolved from WorkerProfile.warehouse, with branch-based fallback for legacy records.

### 4.2 Permission matrix

| Endpoint | Method | Tier 1 | Tier 2 (own facility) | Tier 3 internal | Tier 3 external |
|---|---|---|---|---|---|
| /api/v1/facility-ops/stats/ | GET | all | own | read-only | no |
| /api/v1/facility-ops/stats/ | POST | yes | own | no | no |
| /api/v1/facility-ops/alerts/ | GET | all | own | read-only | no |
| /api/v1/analytics/inventory-alerts/ | GET | all | own | read-only | no |
| /api/v1/ai/assistant/ | POST | yes | auto-scoped | no | no |
| /api/v1/ai/ocr-intake/ | POST | yes | auto-scoped | no | no |
| /api/v1/ai/forecast/<w>/<p>/ | GET | yes | own | no | no |
| /api/v1/ai/redistribution-suggestions/ | GET | yes | no | no | no |
| /api/v1/public/facilities/ | GET | no | no | no | yes |
| /api/v1/public/alerts/ | GET | no | no | no | yes |
| /api/v1/public/facility-stats/<id>/ | GET | no | no | no | yes |

## 5. Endpoint contract summary

### Auth

- POST /api/v1/accounts/auth/login/
- Returns access, refresh, and user payload with role, tier, and warehouse_id.

### Facility operations

- GET /api/v1/facility-ops/stats/
- POST /api/v1/facility-ops/stats/
- GET /api/v1/facility-ops/alerts/

### Analytics

- GET /api/v1/analytics/inventory-alerts/

### AI

- POST /api/v1/ai/assistant/
- POST /api/v1/ai/ocr-intake/
- GET /api/v1/ai/forecast/<warehouse_id>/<product_id>/
- GET /api/v1/ai/redistribution-suggestions/

### Public API (X-API-Key)

- GET /api/v1/public/facilities/
- GET /api/v1/public/alerts/
- GET /api/v1/public/facility-stats/<facility_id>/

## 6. Environment variables

### Backend .env

- DJANGO_SECRET_KEY
- DJANGO_DEBUG
- DJANGO_ALLOWED_HOSTS
- DATABASE_URL
- REDIS_URL
- CORS_ALLOWED_ORIGINS
- JWT_ACCESS_LIFETIME_MIN
- JWT_REFRESH_LIFETIME_DAYS
- GEMMA_API_KEY
- GEMMA_MODEL_ASSISTANT
- GEMMA_MODEL_VISION
- GEMMA_CACHE_TTL_SECONDS
- PUBLIC_API_KEY
- NOTIFICATION_CHANNEL
- EMAIL_BACKEND
- EMAIL_HOST
- EMAIL_PORT
- EMAIL_USE_TLS
- EMAIL_HOST_USER
- EMAIL_HOST_PASSWORD
- DEFAULT_FROM_EMAIL
- SITE_NAME

### Frontend .env

- API_BASE_URL

## 7. Local development

### Backend

```bash
cp .env.example .env
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_facility_demo_data
python manage.py runserver
```

### Frontend

```bash
cd frontend
cp .env.example .env
./deploy/generate-frontend-config.sh
python -m http.server 5500
```

Frontend URL: http://localhost:5500/login.html

On Windows PowerShell:

```powershell
cd frontend
Copy-Item .env.example .env
.\deploy\generate-frontend-config.ps1
python -m http.server 5500
```

## 8. Deploy notes

### 8.1 Frontend config generation on server

Run on each deploy after syncing frontend files:

```bash
cd /srv/afyasync/frontend
cp .env.example .env   # first-time only
# edit .env with API_BASE_URL=https://afyasyc.dima.co.ke/api/v1
./deploy/generate-frontend-config.sh
```

### 8.2 systemd units (backend)

Services required:

- afyasync-backend.service (gunicorn)
- afyasync-celery-worker.service
- afyasync-celery-beat.service

### 8.3 nginx single-host routing

- root serves frontend static files
- /api/ proxies to gunicorn unix socket
- / fallback routes to login.html

## 9. Notifications mode

This build is email-first:

- NOTIFICATION_CHANNEL=email
- Existing SMS implementation remains in integrations.NotificationService and can be re-enabled later with NOTIFICATION_CHANNEL=sms and valid AfricasTalking credentials.

## 10. Gemma quota discipline

- Cache forecast and redistribution responses (GEMMA_CACHE_TTL_SECONDS).
- Keep Reporter and public API Gemma-free.
- Reserve quota for final live demo window.
