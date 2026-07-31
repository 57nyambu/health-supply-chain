# Frontend & API Specification
Smart Health Extension — Track 3 (Build with Gemma: GDG Pwani)
Working name: **AfyaSync** — frontend at `afyasyc.maracore.me`

> Note: this draft has been superseded by `FRONTEND_AND_API_SPEC.md` with the current deployment target (`afyasyc.dima.co.ke`), updated UAC, env variables, and backend/frontend integration details.

---

## 0. Deployment shape (read this first, it changes §1–§7 below)

- **Backend**: Django + DRF + Celery, run as a **systemd service** (gunicorn), reverse-proxied by nginx.
- **Frontend**: still a no-build vanilla HTML/CSS/JS static site, served by the same nginx host at `https://afyasyc.maracore.me`, proxying `/api/` to the backend.
- **SMS is not wired for this build.** `integrations.NotificationService` already supports AfricasTalking SMS — leave that code path in place but dormant, and route all alert notifications through **email** instead. Flip back to SMS later with one settings change, not a rebuild. See §5.
- Everything below is written so a teammate can `git clone`, fill in one `.env` file per side, run it locally, and later deploy it with the same env-variable approach — no hardcoded values anywhere in this spec.

---

## 1. Frontend architecture — one dashboard per access tier, one shared design system

Still vanilla HTML/CSS/JS, no framework, no build step — fastest to get working and safest to demo under time pressure. The change from the original single-page plan: **one HTML entry point per tier**, all pulling from the same CSS/JS so they look identical in style.

### 1.1 Shared design system — `frontend/assets/`

```
frontend/
  assets/
    css/
      tokens.css        # ONE file, all brand colors/spacing/type — every dashboard imports it
      base.css           # resets, base typography
      components.css      # cards, buttons, badges, tables, modals, chat bubble
    js/
      api.js              # fetch wrapper — attaches JWT / X-API-Key, reads base URL from config.js
      config.js            # generated at deploy time from env vars, see §7 — never hand-edited
      auth.js              # login, token refresh, role → dashboard redirect
    icons/                # Lucide icon set (MIT, static SVG, no JS runtime) — don't mix icon sets
  login.html
  admin/index.html         # Tier 1
  facility/index.html      # Tier 2
  reports/index.html       # Tier 3 internal (Reporter)
```

`tokens.css` is the single source of truth for the look — clinical blue/teal primary, neutral grays, red/amber/green reserved *only* for alert severity (never decorative), card-based layout, one type scale. Every dashboard including future ones inherits it automatically; "same styles across tiers" is enforced by file structure, not by convention.

### 1.2 Tier 1 — Admin dashboard (`/admin/`)

| Tab | Source | Gemma-touched |
|---|---|---|
| Facility Overview | `GET /facility-ops/stats/` — all facilities | forecast one-liner per stock card |
| AI Assistant | `POST /ai/assistant/` | full chat, centerpiece screen — most visual polish |
| Alerts Feed | `GET /analytics/inventory-alerts/` + `GET /facility-ops/alerts/` | — |
| Redistribution Suggestions | `GET /ai/redistribution-suggestions/` | `reasoning` field shown per suggestion; "Approve Transfer" → `POST /warehouses/transfers/` |
| OCR Intake | `POST /ai/ocr-intake/` | extracted fields + confidence note before confirm |

### 1.3 Tier 2 — Facility Staff dashboard (`/facility/`)

Same shell and styling, scoped server-side to the logged-in user's own `warehouse_id` — not just hidden client-side.

| Tab | Source | Gemma-touched |
|---|---|---|
| My Facility | `GET /facility-ops/stats/` (own facility) + `POST /facility-ops/stats/` (submit today's figures) | forecast one-liner per stock card |
| AI Assistant | `POST /ai/assistant/` (auto-scoped, see §3) | yes |
| Alerts | `GET /facility-ops/alerts/` (own facility) | — |
| OCR Intake | `POST /ai/ocr-intake/` | yes |

No Redistribution tab here — that endpoint is Tier 1-only both in the nav and on the server (`IsTier1`).

### 1.4 Tier 3 internal — Reporter dashboard (`/reports/`)

Read-only, district-wide, **no AI calls at all** — keeps this tier off the Gemma quota entirely (see §10).

| Tab | Source |
|---|---|
| District Overview | `GET /facility-ops/stats/` (read-only) |
| Alerts | `GET /facility-ops/alerts/`, `GET /analytics/inventory-alerts/` |

### 1.5 Tier 3 external — third-party integrators

No dashboard — they call `/api/v1/public/...` directly with `X-API-Key`. Optional stretch if time allows: a static `public.html` demo page hitting only the public endpoints, to show the open-data story live. Not required for judging.

### 1.6 Login / role routing

`login.html` posts to `POST /accounts/auth/login/`, gets back `access`/`refresh` JWT, reads `role` (from the decoded token or a `GET /accounts/me/` call) and redirects: `ADMIN` → `/admin/`, `{BRANCH_MANAGER, WAREHOUSE, PROCUREMENT, CASHIER}` → `/facility/`, `REPORTER` → `/reports/`.

Known limitation, worth one line in the writeup: this is a static site with no server-side session, so the access token lives in a JS variable and the refresh token in `sessionStorage`. Fine for a one-day build; not how you'd store tokens in a production deployment.

---

## 2. AI integration on the frontend — kept to four touchpoints on purpose

1. **AI Assistant chat** (Tier 1 & 2) — the demo centerpiece, full function-calling exchange visible turn by turn.
2. **Inline forecast line** on each Facility Overview stock card (Tier 1 & 2) — one sentence from `/ai/forecast/`, fetched once per card per session and cached client-side so tab-switching doesn't re-trigger a call.
3. **Redistribution reasoning** (Tier 1 only) — the `reasoning` field rendered as-is under each suggestion, not re-summarized.
4. **OCR Intake confirm screen** (Tier 1 & 2) — extracted fields + `confidence_note` shown before the user commits.

Nothing else calls Gemma from the frontend. Reporter dashboard and the public API are deliberately Gemma-free — that's the quota-protection story from §10, not an oversight.

---

## 3. Permission tiers (UAC)

### 3.1 Matrix

| Endpoint | Method | Tier 1 Admin | Tier 2 Facility (own facility) | Tier 3-internal Reporter | Tier 3-external Public |
|---|---|---|---|---|---|
| `/facility-ops/stats/` | GET | all facilities | own only | read-only, district-wide | — |
| `/facility-ops/stats/` | POST | ✅ | own only | ❌ | — |
| `/facility-ops/alerts/` | GET | all | own only | read-only | — |
| `/ai/assistant/` | POST | ✅ | auto-scoped | ❌ | ❌ |
| `/ai/ocr-intake/` | POST | ✅ | own only | ❌ | ❌ |
| `/ai/forecast/<w>/<p>/` | GET | ✅ | own only | ❌ | ❌ |
| `/ai/redistribution-suggestions/` | GET | ✅ | ❌ | ❌ | ❌ |
| `/warehouses/transfers/` | POST | ✅ | ✅ (existing role) | ❌ | ❌ |
| `/public/facilities/`, `/public/alerts/`, `/public/facility-stats/<id>/` | GET | — | — | — | ✅ `X-API-Key` |

### 3.2 Implementation

Three tiers, built on the existing `accounts.User.Role` — no new roles added.

```python
# apps/ai/permissions.py  (shared by apps/ai and apps/facility_ops)
from rest_framework.permissions import BasePermission

TIER_1 = {'ADMIN'}
TIER_2 = {'BRANCH_MANAGER', 'WAREHOUSE', 'PROCUREMENT', 'CASHIER'}
TIER_3_INTERNAL = {'REPORTER'}

class IsTier1(BasePermission):
    """District-wide admin access."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in TIER_1

class IsTier1OrTier2(BasePermission):
    """Admin, or facility staff scoped to their own facility."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in TIER_1 | TIER_2
        )
    def has_object_permission(self, request, view, obj):
        if request.user.role in TIER_1:
            return True
        # obj must expose `.warehouse` — Tier 2 users are scoped to their own facility
        return getattr(obj, 'warehouse_id', None) == getattr(request.user, 'warehouse_id', None)

class IsInternalReadOnly(BasePermission):
    """REPORTER role — read-only, district-wide."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in TIER_3_INTERNAL
            and request.method in ('GET', 'HEAD', 'OPTIONS')
        )
```

```python
# apps/ai/authentication.py — Tier 3 external integrators (no user account)
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings

class PublicAPIKeyAuth(BaseAuthentication):
    def authenticate(self, request):
        key = request.headers.get('X-API-Key')
        if not key:
            return None
        if key != settings.PUBLIC_API_KEY:
            raise AuthenticationFailed('Invalid API key')
        return (None, None)  # no user object — request.user stays AnonymousUser
```

Tier 2 auto-scoping (used by `/ai/assistant/`, `/ai/forecast/`, `/facility-ops/*`): the view injects `warehouse_id=request.user.warehouse_id` into every underlying query/tool call, so a facility manager physically cannot get data outside their facility — this is enforced in the view layer, not left to the frontend to respect.

For a one-day build, a single shared `PUBLIC_API_KEY` env var is enough. A production version would issue per-integrator keys via a small `PublicAPIKey` model — name this as a "next step" in the writeup, don't build it today.

---

## 4. Environment variables

| Variable | Used by | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | backend | random, never commit |
| `DJANGO_DEBUG` | backend | `True` locally, `False` in prod |
| `DJANGO_ALLOWED_HOSTS` | backend | `afyasyc.maracore.me` in prod, `localhost,127.0.0.1` locally |
| `DATABASE_URL` | backend | `postgres://user:pass@host:5432/afyasync` |
| `REDIS_URL` | backend / Celery | `redis://localhost:6379/0` |
| `CORS_ALLOWED_ORIGINS` | backend | `https://afyasyc.maracore.me,http://localhost:5500` |
| `JWT_ACCESS_LIFETIME_MIN` | backend | default `15` |
| `JWT_REFRESH_LIFETIME_DAYS` | backend | default `7` |
| `GEMMA_API_KEY` | `apps.ai` | from AI Studio, never commit |
| `GEMMA_MODEL_ASSISTANT` | `apps.ai` | e.g. `gemma-4-4b-it` |
| `GEMMA_MODEL_VISION` | `apps.ai` | e.g. `gemma-4-12b-it` |
| `GEMMA_CACHE_TTL_SECONDS` | `apps.ai` | `1200` — backs the 15–30 min cache on forecast/redistribution |
| `PUBLIC_API_KEY` | `apps.ai` public namespace | shared key for Tier 3-external, rotate after the event |
| `NOTIFICATION_CHANNEL` | `integrations.NotificationService` | `email` for this build; `sms` reserved, don't set yet |
| `EMAIL_BACKEND` | notifications | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS` | notifications | your SMTP provider's values |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | notifications | never commit |
| `DEFAULT_FROM_EMAIL` | notifications | `alerts@afyasyc.maracore.me` |
| `API_BASE_URL` | frontend `config.js` | injected at deploy/run time, see §7 — never hardcoded in JS |

Ship a `.env.example` in the backend root with every key above (values blanked) and a matching `frontend/.env.example` with just `API_BASE_URL`, so a new teammate never has to guess what's needed.

---

## 5. Notifications — email now, SMS later

`integrations.NotificationService` already supports both AfricasTalking SMS and email — don't touch that file's structure. For this build:

- Add `NOTIFICATION_CHANNEL` (`email` | `sms`), default `email`.
- Gate the existing AfricasTalking call behind `if settings.NOTIFICATION_CHANNEL == 'sms':` — the SMS code stays in the repo, just unreached.
- `flag_underperforming_facilities` and any `FacilityAlert`/`RTInventoryAlert` trigger send through the email path only.
- Every `User`/`Branch` contact record needs a valid email for the demo to actually deliver — add this to `seed_facility_demo_data`.
- Re-enabling SMS later is a one-line settings change once AfricasTalking credentials are ready — worth stating explicitly in the writeup as a scoped-down-not-cut feature.

---

## 6. Local development

```bash
# backend
cp .env.example .env          # fill in local values
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_facility_demo_data
python manage.py runserver     # http://localhost:8000

# Celery — only needed locally if you're testing flag_underperforming_facilities or async tasks
celery -A config worker -l info
celery -A config beat -l info

# frontend
cd frontend
cp .env.example .env           # set API_BASE_URL=http://localhost:8000/api/v1
./deploy/generate-frontend-config.sh   # writes assets/js/config.js from .env, see §7
python -m http.server 5500     # http://localhost:5500/login.html
```

Local frontend (port 5500) and backend (port 8000) are cross-origin — make sure `CORS_ALLOWED_ORIGINS` includes `http://localhost:5500` or the AI Assistant/alerts calls will silently fail with CORS errors, which is a confusing thing to debug mid-hackathon.

---

## 7. Deployment

### 7.1 Frontend config injection

No build tool, so env values reach the static JS via one generated file, written fresh on every deploy — never hand-edited, never committed:

```bash
#!/usr/bin/env bash
# frontend/deploy/generate-frontend-config.sh
set -euo pipefail
source .env
cat > assets/js/config.js <<EOF
window.AFYASYNC_CONFIG = {
  API_BASE_URL: "${API_BASE_URL}",
};
EOF
```

### 7.2 Backend — systemd services

```ini
# /etc/systemd/system/afyasync-backend.service
[Unit]
Description=AfyaSync Django backend (gunicorn)
After=network.target postgresql.service redis.service

[Service]
User=deploy
Group=deploy
WorkingDirectory=/srv/afyasync/backend
EnvironmentFile=/srv/afyasync/backend/.env
ExecStart=/srv/afyasync/backend/venv/bin/gunicorn config.wsgi:application \
  --bind unix:/run/afyasync/backend.sock --workers 3
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/afyasync-celery-worker.service
[Unit]
Description=AfyaSync Celery worker
After=network.target redis.service
[Service]
User=deploy
WorkingDirectory=/srv/afyasync/backend
EnvironmentFile=/srv/afyasync/backend/.env
ExecStart=/srv/afyasync/backend/venv/bin/celery -A config worker -l info
Restart=on-failure
[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/afyasync-celery-beat.service — schedules flag_underperforming_facilities
[Unit]
Description=AfyaSync Celery beat
After=network.target redis.service
[Service]
User=deploy
WorkingDirectory=/srv/afyasync/backend
EnvironmentFile=/srv/afyasync/backend/.env
ExecStart=/srv/afyasync/backend/venv/bin/celery -A config beat -l info
Restart=on-failure
[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now afyasync-backend afyasync-celery-worker afyasync-celery-beat
```

### 7.3 nginx — single host serving both

```nginx
server {
    listen 443 ssl http2;
    server_name afyasyc.maracore.me;

    ssl_certificate     /etc/letsencrypt/live/afyasyc.maracore.me/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/afyasyc.maracore.me/privkey.pem;

    root /srv/afyasync/frontend;
    index login.html;

    location /api/ {
        proxy_pass http://unix:/run/afyasync/backend.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        try_files $uri $uri/ /login.html;
    }
}
```

Deploy sequence: `git pull` → backend `migrate` → `systemctl restart afyasync-backend` (+ workers if code changed) → rsync `frontend/` to `/srv/afyasync/frontend` → run `generate-frontend-config.sh` on the server with prod `.env` → nginx needs no reload for static file changes.

---

## 8. Endpoint specification

### 8.1 Existing core endpoints (unchanged — summary only)

| Method | Endpoint | Tier | Notes |
|---|---|---|---|
| `POST` | `/api/v1/accounts/auth/login/` | — | Returns `access`/`refresh` JWT |
| `GET` | `/api/v1/products/inventory/` | 1, 2* | *Tier 2 sees only their facility |
| `GET` | `/api/v1/warehouses/warehouses/` | 1, 2 | |
| `POST` | `/api/v1/warehouses/transfers/` | 1, 2 | Creates a `StockTransfer` |
| `GET` | `/api/v1/analytics/inventory-alerts/` | 1, 2, 3-internal | |

### 8.2 New: `apps.facility_ops`

**`GET /api/v1/facility-ops/stats/`** — Tier 1 (all facilities) / Tier 2 (own facility only)
```json
[
  {
    "warehouse": 4,
    "warehouse_name": "Kilifi County Hospital",
    "date": "2026-07-30",
    "patient_footfall": 132,
    "beds_total": 40,
    "beds_occupied": 37,
    "doctors_scheduled": 5,
    "doctors_present": 3
  }
]
```

**`POST /api/v1/facility-ops/stats/`** — Tier 2 (submit own facility's daily figures)
```json
{
  "warehouse": 4,
  "date": "2026-07-31",
  "patient_footfall": 140,
  "beds_total": 40,
  "beds_occupied": 39,
  "doctors_scheduled": 5,
  "doctors_present": 4
}
```

**`GET /api/v1/facility-ops/alerts/`** — Tier 1, 2 (own facility), 3-internal (read-only, district-wide)
```json
[
  {
    "id": 12,
    "warehouse": 4,
    "alert_type": "understaffed",
    "message": "Only 3 of 5 scheduled doctors present for 3 consecutive days.",
    "severity": "high",
    "resolved": false,
    "created_at": "2026-07-31T06:02:00Z"
  }
]
```
Delivery for this alert now goes out over email (§5) via the existing `NotificationService`, not SMS.

### 8.3 New: `apps.ai` (Gemma 4)

**`POST /api/v1/ai/assistant/`** — Tier 1, 2
```json
// Request
{ "query": "Which facilities are low on amoxicillin?" }

// Response
{
  "answer": "Kilifi County Hospital has 2 days of amoxicillin stock left based on current consumption. Malindi Sub-County Hospital has surplus (18 days). Recommend transferring 200 units from Malindi to Kilifi.",
  "tools_called": ["get_low_stock_alerts", "get_transfer_candidates"]
}
```
Tier 2 callers are automatically scoped: the view injects `warehouse_id=request.user.warehouse_id` into every tool call.

**`POST /api/v1/ai/ocr-intake/`** — Tier 1, 2 (multipart image upload)
```json
{
  "extracted": {
    "commodity_name": "Amoxicillin 250mg",
    "quantity": 340,
    "unit": "tablets",
    "date_recorded": "2026-07-29"
  },
  "confidence_note": "Handwriting on quantity was ambiguous — please confirm before saving.",
  "requires_confirmation": true
}
```
Never auto-save without a human confirm step — misread quantities on medical stock are a real-world risk, not just a demo nicety.

**`GET /api/v1/ai/forecast/<warehouse_id>/<product_id>/`** — Tier 1, 2 (own facility)
```json
{
  "product": "Amoxicillin 250mg",
  "warehouse": "Kilifi County Hospital",
  "current_stock": 80,
  "avg_daily_consumption": 38,
  "forecast_days_remaining": 2,
  "recommendation": "Reorder 500 units within 24 hours; consumption has risen 20% week-over-week."
}
```

**`GET /api/v1/ai/redistribution-suggestions/`** — Tier 1 only (district-wide view)
```json
[
  {
    "product": "Amoxicillin 250mg",
    "from_warehouse": 7,
    "from_warehouse_name": "Malindi Sub-County Hospital",
    "to_warehouse": 4,
    "to_warehouse_name": "Kilifi County Hospital",
    "suggested_quantity": 200,
    "reasoning": "Malindi has 18 days of stock at current consumption; Kilifi has 2. Transfer avoids a stock-out with no new procurement needed."
  }
]
```

---

## 9. Open/public API — for third-party integrators

Namespace: `/api/v1/public/`. Read-only, no JWT — authenticated via `X-API-Key`, no live Gemma calls (external traffic never competes for the 1,500/day Gemma quota — these hit the database directly).

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/public/facilities/` | Facility directory: name, county, coordinates, type — no stock quantities |
| `GET` | `/api/v1/public/alerts/` | Active high-severity alerts only — message + severity, no internal figures |
| `GET` | `/api/v1/public/facility-stats/<id>/` | Footfall/bed occupancy summary for one facility |

```json
// GET /api/v1/public/facilities/
// Header: X-API-Key: <PUBLIC_API_KEY>
[
  { "id": 4, "name": "Kilifi County Hospital", "county": "Kilifi", "type": "hospital" }
]
```

Deliberately excluded: exact stock quantities, supplier/pricing data, patient-footfall below facility-level aggregation, and all write operations.

---

## 10. Gemma quota discipline (AI Studio free tier — 1,500 requests/day)

- **Cache, don't re-call.** `/ai/forecast/` and `/ai/redistribution-suggestions/` are cached for `GEMMA_CACHE_TTL_SECONDS` (15–30 min) via Django's cache framework — these are the endpoints most likely to be hit repeatedly while a teammate is polishing the UI.
- **Reserve a demo budget.** Stop ad-hoc testing against the live key at least an hour before judging; rehearse against cached/logged responses instead.
- **Reporter dashboard and the public API never touch Gemma** — by design, not by accident (§1.4, §1.5, §9).
- Limits can move without notice — check the live number in your AI Studio dashboard the morning of the event rather than trusting this document's figure blindly.
- If quota runs out mid-demo, have one pre-recorded fallback clip of the AI Assistant working, as insurance.
