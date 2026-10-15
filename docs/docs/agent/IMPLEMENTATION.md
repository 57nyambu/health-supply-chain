# Implementation Guide

How the rework is executed: three phases, one Claude Code session per phase, everything committed to `main`.

## 1. How the work is organised

| Phase | Theme | Brief | Ends with tag |
|---|---|---|---|
| 1 | Foundation: monorepo split, upgrades, UAC, audit, data protection, storage, patient registry, Next.js shell and design system | `PHASE-1.md` | `phase-1-complete` |
| 2 | Clinical journey reception → completion, inventory for health, billing core, cash and M-Pesa, MOH reporting | `PHASE-2.md` | `phase-2-complete` |
| 3 | Insurance (SHA + SMART + Slade360), banks, cards, reconciliation, eTIMS, hardening, deployment, certification evidence | `PHASE-3.md` | `phase-3-complete` |

A phase starts only when the previous tag exists and its exit criteria passed. Each phase runs in its own session; if a session ends before the phase is done (context, time), the next session resumes the **same** phase from `PROGRESS.md`.

State never lives only in the conversation. It lives in:
- **git** — the history is the log; commit messages say what and why;
- **`docs/agent/PROGRESS.md`** — narrative status, next steps, blockers, spec gaps;
- **`docs/agent/features.json`** — the feature ledger with `passes` flags;
- **the test suites** — the executable definition of done.

## 2. Session protocol

**Start**
1. Read `PROGRESS.md`, then the active `PHASE-n.md`.
2. `git status` (clean?) and `git log --oneline -20`.
3. `make setup` if the toolchain changed; `make check` to confirm green. If red, fixing it is the first task.
4. Choose the next feature: active phase, `passes: false`, dependencies satisfied (`depends_on`). Prefer the order in the phase brief.

**Per feature**
1. Read the code you will change and its tests; read the DESIGN/integration sections the feature references.
2. Write or extend tests from the acceptance criteria first where practical.
3. Implement the simplest design that satisfies the criteria and the compliance register.
4. Verify end to end: API tests, then the UI flow in a real browser via Playwright for UI features.
5. `make check` → commit (one feature, or one coherent step of it) → push.
6. Flip `passes` only after verification; add a one-line entry under "Done this session" in `PROGRESS.md`.

**End (or when context is getting long)**
1. Finish or cleanly park the current feature (never leave `main` red; park work-in-progress behind a feature flag or keep it uncommitted only if trivial to redo).
2. Update `PROGRESS.md`: done, next, blockers, spec gaps, decisions taken.
3. Commit docs; push.

## 3. Git rules

- **Branch:** `main` only (owner decision). Remote: `origin`.
- **Messages:** Conventional Commits — `feat(billing): post bed-day charges idempotently`; body says why; footer `Refs: P2-IPD-01`. Keep the attribution trailers Claude Code adds.
- **Size:** one feature or one coherent step. Mechanical moves (`git mv`) are separate commits from behaviour changes so history stays readable.
- **Before every commit:** `make check` green. Docs-only commits may use `make check-fast`.
- **Never:** force-push, rewrite history, `--no-verify`, commit `.env*` (except `.env.example`), `data/`, database files, dumps, logs, or any PHI.
- **Phase end:** annotated tag `phase-n-complete` with a summary; push the tag.
- **Pre-existing failures:** don't commit on top of red. Fix, or if it's out of scope and blocking, record it in PROGRESS.md and make it the next task.

## 4. Toolchain

| Tool | Version policy |
|---|---|
| Python | 3.12 (3.13 acceptable), managed by `uv` (`pyproject.toml` + `uv.lock`) |
| Django | 5.2 LTS, latest patch (4.2 reached end of life on 7 April 2026) |
| Django REST Framework | latest release supporting Django 5.2 |
| PostgreSQL | 17 |
| Redis | 7 (Valkey 8 acceptable) |
| Celery | 5.5+ |
| Node.js | 24 LTS |
| pnpm | 10 |
| Next.js | 16.x latest patch (Next 15 support ends 21 October 2026) |
| React | 19 |
| Tailwind CSS | 4 |
| Playwright | latest |
| Docker Compose | v2 |

At each phase start, check for patch releases and apply them in a separate `chore(deps)` commit. Major upgrades need an ADR. Before using any library API you are not certain of, read the docs for the installed version (Context7 MCP if available, otherwise the official docs).

## 5. Make targets (contract — create them in Phase 1)

| Target | Does |
|---|---|
| `setup` | install api (uv) and web (pnpm) deps, Playwright browsers, copy `.env.example` → `.env` if missing (dev-safe defaults only), start compose services |
| `dev` / `down` | start/stop the dev stack |
| `test`, `test-api`, `test-web` | pytest / vitest |
| `e2e` | Playwright scenario suite (fake integrations, seeded data) |
| `lint`, `typecheck` | ruff, mypy, eslint, tsc |
| `check` | the commit gate (§6) |
| `check-fast` | lint + typecheck + unit tests only |
| `migrations-check` | fail on missing migrations |
| `openapi` | regenerate `api/openapi.yaml` and `web/src/lib/api/schema.d.ts` |
| `role-matrix` | regenerate `docs/generated/role-matrix.csv` |
| `traceability` | regenerate `docs/generated/traceability.md` from `req("KE-…")` markers |
| `contrast` | design-token contrast check |
| `seed` / `reset-dev` | synthetic data / wipe dev DB and `data/` (dev only; refuses if `DJANGO_ENV=prod`) |
| `audit-verify` | verify the audit hash chain |

## 6. The commit gate: `make check`

1. `ruff check` and `ruff format --check`
2. `mypy` (strict for new apps; legacy apps may have a documented baseline that only shrinks)
3. `pytest` with coverage: ≥ 85% lines overall; ≥ 95% for `access`, `audit`, `billing`, `payments`, `insurance` services and policies
4. `migrations-check`
5. OpenAPI drift check (generated schema equals committed schema)
6. `eslint`, `tsc --noEmit`, `vitest`
7. `contrast`
8. `gitleaks` (secret scan) on staged changes
9. Playwright smoke (login, open one workspace, axe clean)

The full Playwright scenario suite runs in `make e2e`, in CI on every push to `main`, and is mandatory before a phase tag.

## 7. Testing strategy

| Layer | Tooling | Notes |
|---|---|---|
| Unit | pytest, factory_boy | services, policies, mappers |
| API | DRF test client | every endpoint: happy path, validation, authz denied, audit written |
| Policy matrix | pytest param from `role-matrix.csv` | every role × permission cell |
| Property | hypothesis | money rounding, allocations, ledger balance, stock never negative, sequences gap-free |
| Concurrency | `transaction=True` tests with threads | double callbacks, stock decrement, invoice numbering, bed assignment |
| Contract | shared suite per port | runs against fakes; against sandboxes with `RUN_LIVE=1` |
| Scenario E2E | Playwright | one spec per COMPLETION.md scenario; traces + screenshots on failure |
| Accessibility | @axe-core/playwright | serious/critical = 0 |
| Load | locust | Phase 3, targets in DESIGN §16 |

Mark tests with `@pytest.mark.req("KE-…")` where they prove a regulatory requirement. Never weaken, skip or delete a test to get green; if a test is wrong, fix it and say why in the commit body.

## 8. Data, fixtures and seeds

- `make seed` creates a synthetic organisation: one facility with test MFL code `99999` (KEPH level 4), departments, service points, wards and beds; one user per role (password from `SEED_PASSWORD`; MFA bypass only when `DJANGO_ENV=dev`); 500 synthetic patients from curated Kenyan-plausible name lists (no real people); price lists for cash, SHA and two insurers; a drug catalogue with batches and expiries; a clearly-marked **synthetic** SHA intervention subset; triage scales.
- Identifiers in seeds use obviously fake ranges (national IDs starting `000`), phones from provider sandboxes.
- Fixtures recorded from vendor sandboxes are sanitised before commit (script: `scripts/sanitize_fixture.py`).
- Never import production data into dev; never commit dumps.

## 9. External integrations: build order and spec gaps

For every integration: **port → fake → contract tests → sandbox adapter → recorded fixtures → live configuration**. The fake is a first-class product feature (`*_MODE=fake`), used in dev, CI and demos.

Spec gap entry (in PROGRESS.md):
```
- [GAP-SMART-003] SMART claim submission: field for practitioner ID unknown.
  Assumption in fake: regulator + registration number. Risk: adapter rework.
  Owner action: request API spec section "claims" from SMART partner team.
```

## 10. Phase dependencies

```
P1 repo/upgrade ─► P1 settings/API conventions ─► P1 UAC + audit ─► P1 data protection ─► P1 storage
                                         └────────► P1 web scaffold ─► design system ─► auth UI ─► admin/reception UI
P1 facilities + patients ─► P2 visits/queues ─► P2 triage/consult/orders ─► P2 lab/imaging/pharmacy/IPD
P2 billing core ─► P2 payments core ─► P2 cash + M-Pesa ─► P3 banks/cards/reconciliation
P2 billing + clinical ─► P3 insurance port ─► P3 SHA ─► P3 SMART/Slade360 ─► P3 claims workbench
everything ─► P3 hardening, deployment, evidence pack
```

## 11. Self-review before each commit

- New or changed endpoint: permission declared, object scoping in selector, audit event written, OpenAPI updated.
- No PHI in logs, errors, URLs, analytics, SMS bodies, fixtures.
- Money is `Decimal`; rounding explicit; ledgers balance.
- External calls via an adapter with timeouts; writes idempotent; callbacks verified.
- Migrations reversible or explained; no edits to applied migrations.
- UI: keyboard path works, focus visible, axe clean, copy follows DESIGN-SYSTEM §9.
- Docs updated when behaviour, env vars or procedures change (`.env.example`, SOPs, integration docs).

## 12. When something is unclear

1. Look in DESIGN.md, the integration docs and the compliance register.
2. Regulatory or external-API uncertainty: check the primary source (hie-docs.dha.go.ke, afyalink.dha.go.ke, kenyalaw.org, odpc.go.ke, the provider's developer portal); record the finding and source in DECISIONS.md.
3. Lasting technical choice: write an ADR, then implement.
4. Business choice only the owner can make: write the question in PROGRESS.md "Questions for owner" with options and your recommendation, continue with the documented default (DESIGN §20) or with other features, and flag it in your end-of-session summary.
