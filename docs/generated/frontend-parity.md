# Frontend parity checklist (P1-WEB-06)

Source: `docs/legacy/FRONTEND_AND_API_SPEC.md` (the current spec; the older draft is `docs/legacy/FRONTEND_AND_API_SPEC-draft.md`), the tracked `frontend/` dashboards, and the untracked React SPA `afyasync-frontend/` in the owner's checkout (its own repository; inventoried 2026-10-15). Every item is either **ported** to `web/` (route given) or **dropped** with the reason. Checked 2026-10-16 against the Playwright scenarios named in the last column.

By the time of this port the legacy dashboards no longer worked: they signed in with SimpleJWT bearer tokens, which P1-UAC-04 removed, and their AI panels call endpoints closed by ADR-014.

## Dashboards and views

| Legacy | What it showed | Status | Where now | Proof |
|---|---|---|---|---|
| `frontend/login.html`, SPA `/login` | E-mail + password, JWT in `sessionStorage` | Ported | `/login` → `/mfa` / `/mfa/setup` (session cookie, httpOnly; MFA for privileged roles; lock screen) | `auth.spec.ts`, `smoke.spec.ts` |
| SPA `/signup` | Self-registration | **Dropped** | Accounts are created by a facility administrator, with privileged roles approved by a second administrator (DESIGN §7.2, §7.9) | `admin.spec.ts` |
| `/admin` (tier 1) — Overview | Facility cards: patient footfall, bed occupancy, attendance, per facility | Ported | `/reports` → "Facility operations" (latest-day figures, 7-day total, daily table). Facilities are chosen with the facility switcher instead of one card per facility | `operations.spec.ts` |
| `/admin` — Alerts | Facility alerts and inventory (low-stock) alerts | Ported | `/reports` → "Facility alerts", "Low-stock alerts" | `operations.spec.ts` |
| `/admin` — AI Assistant (Gemma) | Free-text chat over facility data | **Dropped** | Sends facility and stock data to an external AI service; disabled until a DPIA covers it (ADR-014, `AI_FEATURES_ENABLED=false`) | `apps/ai` tests |
| `/admin` — Suggested redistribution (Gemma) | AI stock-move suggestions | **Dropped** | Same as above (ADR-014). Stock transfers stay available in the API (`/api/v1/warehouses/transfers/`); their screens come with Phase 2 inventory | — |
| `/admin` — OCR intake (Gemma vision) | Upload a photo of a delivery note, AI reads it | **Dropped** | Uploaded images went to an external AI service with the key in the URL (ADR-014). Goods received will be entered in the Phase 2 inventory screens; documents go through `documents.storage` | — |
| `/admin` — Forecast line on cards | AI demand forecast per facility | **Dropped** | ADR-014 | — |
| `/facility` (tier 2) — My facility | Own facility's stats cards | Ported | `/inventory` → "Daily figures" (scoped to the active facility by the API) | `operations.spec.ts` |
| `/facility` — Alerts | Own facility and low-stock alerts | Ported | `/inventory` → "Low-stock alerts", "Facility alerts" | `operations.spec.ts` |
| `/facility` — AI Assistant, OCR intake, forecast | AI panels | **Dropped** | ADR-014 | — |
| `/reports` (tier 3 internal, read-only) — Overview, Alerts | Stats and alerts, no AI | Ported | `/reports` (report viewer role: read-only, no AI) | `operations.spec.ts` |
| SPA `/system-overview` | Cross-facility summary charts | Ported (as tables) | `/reports` "Facility operations"; charts are replaced by figures and a table (accessible, printable). Trend charts come with the Phase 2 MOH reports | `operations.spec.ts` |
| SPA demo mode | Canned data without a backend | **Dropped** | The synthetic seed (`make seed`) gives every environment realistic, PHI-free data | `make seed` |
| Statistics entry (`POST /api/v1/facility-ops/stats/`) | API only in the legacy app (no screen) | Unchanged | Still API only (`operations.stats.submit`, own facility, audited). In Phase 2 footfall and bed figures come from visits and admissions instead of manual entry | `apps/facility_ops` tests |

## Cross-cutting behaviour

| Legacy | Status | Now |
|---|---|---|
| Tier model (ADMIN / BRANCH_MANAGER… / REPORTER) | Ported | Roles and permissions from `/api/v1/me`; workspaces shown only when a permission allows them; the API enforces access (default deny) |
| Tier-2 scoping by `WorkerProfile.warehouse` | Ported | Scoped to the active facility (`warehouse.branch → Facility`, ADR-018) |
| JWT in `sessionStorage` | **Dropped** | Session cookie (httpOnly, SameSite), CSRF on unsafe requests, nothing in browser storage (web/CLAUDE.md) |
| `config.js` / `generate-frontend-config.{sh,ps1}` (API base URL per deploy) | **Dropped** | Same origin: nginx sends `/api/` to Django and `/` to Next.js; no per-deploy config file |
| Bootstrap Icons from jsDelivr CDN | **Dropped** | lucide icons bundled with the app; no third-party CDN at runtime |
| `tokens.css` / `base.css` / `components.css` | Replaced | Flat 2.0 high-contrast design system (`web/src/styles/tokens.css`, DESIGN-SYSTEM.md), contrast-checked in `make check` |
| nginx: root serves `frontend/`, `/` falls back to `login.html` | Replaced | `infra/nginx/afyasync.dima.co.ke.conf`: `/` → Next.js standalone (`infra/systemd/afyasync-web.service`), `/api/` → gunicorn |
| Public API (`X-API-Key`) | Not a frontend | Stays for non-PHI data with one hashed key per integrator (P1-UAC-03) |

## Removal

`frontend/` is deleted in its own commit after this checklist (P1-WEB-06). `afyasync-frontend/` is not part of this repository and is not touched; the owner can archive that repository once `web/` is deployed.
