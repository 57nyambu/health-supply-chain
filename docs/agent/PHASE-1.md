# Phase 1 — Foundation and Access Control

**Goal:** a restructured, upgraded, secure foundation that later phases build on: `api/` + `web/` monorepo, Django 5.2 LTS, default-deny UAC with care-team access and break-glass, tamper-evident audit, field encryption, switchable storage, facility and patient registry, Next.js 16 shell with the Flat 2.0 high-contrast design system, CI.

**Session:** one Claude Code session (resume from `PROGRESS.md` if it ends early). Commit to `main`; tag `phase-1-complete` at the end.

## Entry criteria
- The agent docs are committed at the repo root (`CLAUDE.md`, `api/CLAUDE.md`, `web/CLAUDE.md`, `.claude/settings.json`, `docs/`).
- Docker, Python 3.12, uv, Node 24, pnpm available (`make setup` will check once it exists; before that, check manually and note gaps in PROGRESS.md).

## Read first
`CLAUDE.md`, `IMPLEMENTATION.md`, DESIGN §1–5, §7, §8, §13, §17–19, `DESIGN-SYSTEM.md`, `docs/integrations/STORAGE.md`, the legacy `README.md`, `FRONTEND_AND_API_SPEC.md`, and the legacy code you will move.

## Before writing code (first hour)
1. Inventory the legacy repo: apps, models, migrations, URLs, settings, tests (and whether they pass), `frontend/` technology, `ai` endpoints, integration code, anything secret-looking in the tree. Write the findings to PROGRESS.md ("Legacy inventory").
2. Run the legacy test suite as-is and record the baseline.
3. Confirm the plan below still fits what you found; if not, record an ADR and adjust the order (not the acceptance criteria).

## Work order

| # | Feature | Notes |
|---|---|---|
| 1 | P1-REPO-01 | `git mv` only, separate commit; then fix imports/settings in a second commit. Rename `root` → `config` (ADR-003). |
| 2 | P1-REPO-02 | Report secrets; never rewrite history yourself. |
| 3 | P1-API-01 | Upgrade path 4.2 → 5.2: run with `-Wd`, fix deprecations, update third-party packages. Postgres in tests. |
| 4 | P1-API-02, P1-API-03, P1-API-04 | Settings split, conventions, observability. |
| 5 | P1-OPS-01, P1-QA-01 | Compose (ports on 127.0.0.1 only), Makefile, Jenkinsfile. From here, `make check` is the gate. |
| 6 | P1-UAC-01, P1-UAC-10, P1-UAC-03 | Permission catalogue, maker-checker primitive, default deny. Expect many legacy views to need policies — do it systematically with the URLconf test as the to-do list. |
| 7 | P1-UAC-04, P1-UAC-05, P1-UAC-06 | Auth, MFA, workstation lock. |
| 8 | P1-UAC-07, P1-UAC-02 | Licences; scoped assignments. |
| 9 | P1-FAC-01, P1-DATA-01, P1-PAT-01 | Facilities, encryption, patients. |
| 10 | P1-AUD-01, P1-UAC-08, P1-UAC-09 | Audit, care-team access, sensitivity. |
| 11 | P1-DATA-02, P1-STO-01, P1-STO-02, P1-PAT-02 | Consents/DSAR, storage, Client Registry port. |
| 12 | P1-WEB-01, P1-WEB-02 | Next.js scaffold, design system (contrast script, fonts, components, `/design`). |
| 13 | P1-WEB-03, P1-WEB-04, P1-WEB-05 | Auth UI, admin, reception. |
| 14 | P1-WEB-06 | Port legacy dashboards; delete `frontend/` after the parity checklist. |
| 15 | P1-E2E-01 | E2E-11, E2E-12, E2E-15; phase exit. |

## Decisions already made (don't re-litigate; ADR to change)
- Django 5.2 LTS, not 6.x (ADR-002). Next.js 16 (ADR-004). Session auth via same-origin `/api` (ADR-005).
- Local storage default; S3-compatible switch; residency guard (ADR-006, ADR-007).
- Keep `accounts` app name and the custom user model.
- Trunk-based on `main` (ADR-001).

## Pitfalls to avoid
- Moving files and changing behaviour in one commit (history becomes unreadable).
- Leaving any legacy endpoint reachable without a policy "for now".
- Logging request bodies while debugging auth (PHI/password leaks). Use the scrubbing filter from day one.
- Building UI before the API returns effective permissions (`/api/v1/me`) — the shell depends on it.
- Treating the fake Client Registry as optional — reception must work offline from the HIE.

## Exit criteria
- Every Phase 1 feature in `features.json` has `passes: true`.
- `make check` and `make e2e` green on a fresh clone (`git clone` → `make setup` → `make seed` → `make e2e`).
- `docs/generated/role-matrix.csv` and `docs/generated/frontend-parity.md` committed.
- No view without a policy; no plaintext identifiers in the DB; `make audit-verify` passes.
- PROGRESS.md has the Phase 1 summary, open spec gaps, owner actions, and the recommended first steps for Phase 2.
- Annotated tag `phase-1-complete` pushed.
