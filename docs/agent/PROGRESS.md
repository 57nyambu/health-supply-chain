# Progress Log

The agent updates this file at the end of every session (and before context runs low). Newest session on top. Keep it factual and short; details belong in commits.

## Current state
- **Active phase:** 1 (in progress)
- **Last tag:** none
- **`main` status:** legacy has no tests; `manage.py check` clean (see Legacy inventory)
- **Next feature:** P1-REPO-01

## Owner actions (external, long lead time — start now)
- [ ] Decide production hosting for real patient data (ADR-006): Kenya-hosted, or Contabo with documented legal basis
- [ ] HIE/SHA: request UAT credentials, get the current SHA Benefits and Tariffs spreadsheet, confirm facility FID(s)
- [ ] DHA certification: register on certification.dha.go.ke (business account); plan the UAT demo
- [ ] ODPC: registration for each facility (controller) and for the vendor/host (processor)
- [ ] SMART and Slade360: integration agreements, API specs, test credentials
- [ ] Daraja (shortcode, passkey, initiator), JengaHQ merchant onboarding, KCB Buni app + go-live letter, Pesapal merchant account
- [ ] KRA eTIMS: decide system-to-system (OSCU/VSCU) or KRA tools at go-live
- [ ] Public API integrators: the shared `PUBLIC_API_KEY` is gone (P1-UAC-03). Create one key per integrator with `python manage.py create_api_client --name <who>` and send it securely; keys are stored only as HMACs
- [ ] After deploying Phase 1, review the administrators created from legacy ADMIN users (ADR-019) and grant branch managers the roles they still need
- [x] Rotate any secrets the P1-REPO-02 scan finds — full-history gitleaks scan (2026-10-15) found none; no history rewrite needed

## Questions for owner
<!-- - [Q-001] question — options — recommendation — default used meanwhile -->

## Spec gaps
<!-- - [GAP-XXX-NNN] integration/operation — unknown — assumption in fake — risk — owner action -->

## Legacy inventory
Taken 2026-10-15 at `1789300` (before P1-REPO-01).

**Stack.** Django 4.2 (unpinned `requirements.txt`, 70 packages, no lock), DRF, SimpleJWT (+ `token_blacklist`), drf-spectacular, django-cors-headers, Celery + Redis, Channels (imported, not installed), africastalking, resend, requests. Settings package `root/settings/{base,development,production}.py` (no `__init__` selection; `manage.py` → development, wsgi/asgi → production). Dev DB SQLite by default (`dj_database_url`), production Postgres. Dev/prod logging writes `error.log`, `db_transactions.log` (all SQL at DEBUG), `debug.log` into the repo root.

**Apps (`apps/`, all `apps.<name>`).**
| App | Models | Endpoints | Notes |
|---|---|---|---|
| core | `BaseModel` (abstract), `Configuration`, `AuditLog` | `api/v1/mgt/` → POS template (no auth) | tier helpers in `core/permissions.py`; second `PublicAPIKeyAuthentication` (unused duplicate of `ai.authentication`) |
| accounts | `User` (email login, `role` of 6 retail roles, `phone` plaintext, `failed_login_attempts`, `account_locked`), `WorkerProfile` (`branch`, `warehouse`, `id_number`, `signature` image, `pin_code` **plaintext**) | `users`, `profiles`, `auth/login`, `auth/logout` — mounted twice (`api/v1/accounts/`, `api/v1/auth/`) | login returns SimpleJWT access/refresh **and** creates a session; `User.save` writes `AuditLog`; post_save queues `send_welcome_credentials_task` (emails a plaintext temp password and overwrites the password set by the admin); `accounts/signals.py` never connected |
| warehouses | `Branch` (KRA PIN, county, …), `Warehouse`, `BinLocation`, `StockTransfer` | `branches` (IsAdminUser), `warehouses`, `bins`, `transfers` (IsAuthenticated, little scoping) | legacy dashboards treat `Warehouse` as the "health facility" |
| products | `Category`, `Product` (Decimal prices; `vat_amount` multiplies Decimal by float 0.16 → TypeError), `ProductImage`, `Inventory` | categories/products/inventory/images (IsAuthenticated or role lists) | |
| suppliers | duplicate copies of products' `Category/Product/ProductImage/Inventory` tables | none | dead models, migrations applied |
| procurement | none | none | empty |
| sales | `Customer` (name, phone plaintext), `Order`, `OrderItem`, `Receipt` | `sales/pos/`, `sales/process-payment/` — **plain Django views with no authentication**; the latter triggers an M-Pesa STK push | receipt/status SMS via signals |
| integrations | `Notification`, `InventoryAlert` | none (urls commented out) | `mpesa.py` (sandbox URLs hard-coded, no timeouts, no idempotency); `sms.py` reads `settings.AFRICASTALKING_*` which don't exist → `NotificationService()` raises on construction, so welcome/alert notifications always fail |
| analytics | `SalesReport`, `RTInventoryAlert` | `analytics/inventory-alerts/` | `signals.py` imports `sales.models` (wrong path) and is never connected; Channels consumer + routing not wired |
| facility_ops | `FacilityDailyStats`, `FacilityAlert` (both keyed on `warehouses.Warehouse`) | `facility-ops/stats/` (GET/POST), `facility-ops/alerts/` | seed command `seed_facility_demo_data`; beat task `flag_underperforming_facilities` |
| ai | none | `ai/assistant/`, `ai/ocr-intake/`, `ai/forecast/<w>/<p>/`, `ai/redistribution-suggestions/`; public `public/facilities/`, `public/alerts/`, `public/facility-stats/<id>/` (shared `X-API-Key`, non-constant-time compare, no rate limit) | sends prompts **and uploaded images** to Google Generative Language API with the key in the URL query string → must be disabled (ADR-014) |
| temp | none | none | not in `INSTALLED_APPS`; dead |

Also: stray packages `apps/migrations/`, `root/migrations/`, `static/migrations/`, `templates/migrations/` (created by `apps/reset.ps1`, which only creates missing `migrations/__init__.py` files — dev-only, harmless). Templates: `templates/sales/pos.html`, `templates/emails/welcome_cred.html` (the code renders `integrations/emails/*.html`, which don't exist). `schema.yaml` (49 KB) is a stale drf-spectacular export. `deploy/` has a systemd unit (`root.settings.production`, gunicorn on 127.0.0.1:8000) and an nginx vhost serving a SPA from `/home/afya-front/frontend/dist`.

**URLs.** 98 routes outside `/admin/`; every DRF view uses `IsAuthenticated`, `IsAdminUser` or tier/role classes — there is no default-deny and no object-level policy beyond tier-2 warehouse scoping. `api/schema/` and docs are `staff_member_required`.

**Tests baseline.** No tests exist. `.gitignore` contains `tests*`, which would silently ignore any new test directory — fixed in P1-REPO-02. With Django 4.2.30 on SQLite: `manage.py check` → no issues; `makemigrations --check` → no changes; `migrate` applies 47 migrations cleanly; `manage.py test` → "Ran 0 tests".

**Frontends — three of them.**
1. `frontend/` (tracked): vanilla HTML/CSS/JS dashboards `login.html`, `admin/`, `facility/`, `reports/` (tabs: overview, assistant, alerts, redistribution, OCR); JWT kept in `sessionStorage`; Bootstrap Icons from jsDelivr CDN.
2. `afyasync-frontend/` (**untracked** in the owner's main checkout; its own git repo `github.com/alice09072004/afyasync-frontend`): React 19 + Vite 8 + Tailwind 3 SPA with routes `/login`, `/signup`, `/system-overview`, `/admin`, `/facility`, `/reports`, TanStack Query, recharts charts, AI chat and OCR panels, demo mode. This is what the nginx vhost serves. Not in this repo, so it is not moved or deleted; its screens are included in the P1-WEB-06 parity checklist.
3. `FRONTEND_AND_API_SPEC.md` exists in three copies: root `FRONTEND_AND_API_SPEC.md` (current, 5.6 KB — the parity source), root `FRONTEND_AND_API_SPEC (1).md` (older 21 KB draft, marked superseded) and `afyasync-frontend/FRONTEND_AND_API_SPEC (1).md` (the same draft without the superseded note). P1-REPO-01 moves the two tracked copies to `docs/legacy/`.

**Secrets.** `gitleaks git` over all 10 commits: 1 finding, `README.md:425` (`Authorization: Token YOUR_API_TOKEN`) — a placeholder, not a secret. No `.env`, database, log or key files were ever committed. Nothing to rotate from the repository; the deployed server's `.env` is outside the repo.

**Personal data.** Legacy PHI-like fields: `User.phone`, `WorkerProfile.id_number`/`pin_code`, `Customer.name/phone` (retail customers). No patient tables yet.

**Environment on this machine (entry criteria).** Docker **missing** (compose cannot be run here — compose files are written but verified only by CI); Python 3.12 registered but broken → using Python 3.13.0 (allowed by IMPLEMENTATION §4); uv installed (0.13.1, user pip); Node 22.18 (not 24) with pnpm 11.1.3; GNU make 4.4.1 and gitleaks 8.30.1 installed via winget (user scope); PostgreSQL 16.2 and Redis 5 run as Windows services — the agent has no credentials for the system Postgres, so tests use a private trust-auth cluster on `127.0.0.1:5433` (`scripts/dev/local-postgres.sh`).

**Plan check.** The PHASE-1 order fits. Adjustments, each recorded where it happens:
- Legacy browser auth is SimpleJWT bearer tokens (not DRF `TokenAuthentication`); P1-UAC-04 removes JWT authentication and blacklists outstanding refresh tokens.
- DESIGN §4 makes `Facility` 1:1 with `warehouses.Branch`, but legacy dashboards key facility data on `Warehouse`; `Facility` follows DESIGN and legacy facility_ops data reaches it via `warehouse.branch` (ADR-018, P1-FAC-01).
- The unauthenticated `sales` views and the AI endpoints are closed in P1-UAC-03 (AI behind `AI_FEATURES_ENABLED=false`).

## Session log

### Session 2026-10-15 — Phase 1
Done this session:
- Doc pack layout fixed (`1789300`); legacy inventory recorded (`8aa220b`)
- P1-REPO-01 (in progress) — legacy code moved to `api/` with `git mv` (`2cd1c0b`), imports/settings fixed (`14a355b`); waits for `web/` (P1-WEB-01) and compose/Jenkinsfile (P1-OPS-01, P1-QA-01)
- P1-REPO-02 — ignore rules (legacy `tests*`/`backup*` patterns removed), `.gitleaksignore` for the reviewed placeholder, ENV docs + test (`f1f3c44`, P1-API-02 commit)
- P1-API-01 — Django 5.2.18 on uv/pyproject, pytest, PostgreSQL only, dead modules removed (`0884976`)
- P1-API-02 — `config/settings/{base,dev,test,prod}.py` by `DJANGO_ENV`, production guards with a test per guard, `docs/operations/ENV.md`
- P1-API-03 — problem+json, request IDs, pagination classes, Idempotency-Key middleware, OpenAPI 3.1 + drift test (`20c7025`)
- P1-API-04 — /healthz, /readyz, scrubbed JSON logs, residency-gated error tracker (`460ecae`)
- P1-OPS-01 / P1-QA-01 (in progress) — Makefile (`make check` is the gate from `aa7b0df`), compose, Dockerfile, Jenkinsfile; compose and Jenkins not executable here (no Docker)
- P1-UAC-01 — permission catalogue (144 codes), 32 seeded roles, role matrix + per-cell test (`37a82b8`)
- P1-AUD-01 (in progress) — hash-chained audit, anchors, `make audit-verify`, append-only triggers, prod grant revocation (`44ea058`); viewer API and PHI-read logging pending
- P1-FAC-01 (in progress) — facilities, departments, service points, wards, beds (`d26d464`); admin API pending
- P1-UAC-10 — maker-checker approvals (`293a922`)
- P1-UAC-02 — scoped/time-bound assignments, privileged grants with second approver, session revocation on deactivation, legacy role migration ADR-019 (`729114a`)
- P1-UAC-03 — default deny on every view, URLconf tests, legacy endpoints reworked or removed, API-key service accounts (`7deda80`)

<!--
### Session YYYY-MM-DD — Phase n
Done this session:
- P1-XXX-NN — one line on what changed (commit abc1234)
Verified:
- make check ✔, make e2e ✔ (or what failed and why)
Next:
- P1-XXX-NN — first step
Blockers / risks:
- …
Decisions:
- ADR-0NN …
-->
