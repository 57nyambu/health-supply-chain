<!-- Maintainer note (stripped from the agent's context): keep this file under ~170 lines. It routes to docs/; it does not repeat them. Nested api/CLAUDE.md and web/CLAUDE.md load when the agent works in those folders. -->

# AfyaSync HMIS — agent instructions

You are turning this repository — a Kenyan retail inventory system with a health add-on (AfyaSync) — into a hospital management information system that a Kenyan facility can run from reception to completion of treatment, that integrates with SHA through the national Health Information Exchange, and that can pass Digital Health Agency (DHA) certification. Patients' safety, money and privacy depend on this code: prefer correct, explicit and boring over clever.

## Every session starts like this
1. Read `docs/agent/PROGRESS.md` — where things stand, what's next, open blockers.
2. Read the active phase brief `docs/agent/PHASE-<n>.md`. One phase is active at a time; the phase changes only after the previous `phase-<n>-complete` tag exists.
3. `git status`, `git log --oneline -20`, then `make check` (before Phase 1 creates it: the legacy test command). If `main` is red, fixing it is the first task.
4. Pick the next feature from `docs/agent/features.json`: active phase, `passes: false`, dependencies passing. Work on one feature at a time.

Read the parts of `docs/agent/DESIGN.md` and the integration docs that the feature references — they are long; don't load all of them every time.

## Every session ends like this (or earlier, when context runs low)
- Leave `main` green; commit and push finished work.
- Update `PROGRESS.md`: done, next, blockers, spec gaps, questions for the owner, decisions.
- Set `"passes": true` only for features whose acceptance criteria you verified end to end in this session. Never edit acceptance criteria to make something pass; if a criterion is wrong, say why in PROGRESS.md and ask.

## Repository map (target after P1-REPO-01)
```
api/     Django 5.2 LTS + DRF — modular monolith, apps/<domain>/   (rules: api/CLAUDE.md)
web/     Next.js 16 App Router + TypeScript — role workspaces       (rules: web/CLAUDE.md)
infra/   docker compose (dev/prod), nginx, Jenkinsfile, backup scripts
data/    local object storage root — git-ignored; real patient files in production; never read it
docs/    agent/ (design, phases, ledger, ADRs), compliance/, integrations/, operations/, evidence/, generated/
```

## Commands (Makefile — created in P1-OPS-01)
- `make setup` · `make dev` · `make down` · `make seed`
- `make test` (pytest + vitest) · `make e2e` (Playwright scenarios) · `make lint` · `make typecheck`
- `make check` — the commit gate: lint, types, tests with coverage, migrations check, OpenAPI drift, contrast, secret scan, Playwright smoke
- `make openapi` · `make role-matrix` · `make traceability` · `make audit-verify`

## Non-negotiables — and why
1. **Default deny.** Every API view declares a permission policy; `test_every_view_has_policy` must pass. An HMIS without object-level access control is a data breach waiting to happen (DESIGN §7).
2. **No PHI where it doesn't belong:** logs, URLs, error messages, analytics, SMS/email bodies, commit messages, fixtures, seed data. Use synthetic data only. Health data is sensitive personal data under the Data Protection Act 2019.
3. **Audit every read and write of patient data** through the audit service/middleware. Audit rows are never updated or deleted.
4. **Clinical and financial records are append-only.** Corrections are amendments or credit notes with a reason; no hard deletes.
5. **Money is `Decimal`** (2 dp, KES, explicit rounding), strings in the API, never floats. Ledgers balance; allocations never exceed amounts.
6. **External systems only through adapters** (`apps/<app>/adapters/`): timeouts, retries for reads only, idempotency keys for writes, raw payloads encrypted. Never invent request/response fields — use `docs/integrations/*`, vendor specs or recorded sandbox traffic; when a spec is missing, build port + fake + contract tests and log a spec gap.
7. **Never auto-retry money movement or claim submission.** On an uncertain outcome, query the provider/payer first.
8. **Emergencies are never blocked by payment or eligibility, and discharge is never blocked by an unpaid balance** (Constitution Art. 43(2); Health Act; court rulings — ADR-013). Tests enforce both; never remove them.
9. **Files only through `documents.storage`** (local `data/` by default, S3-compatible by switch); never public URLs; never write user files elsewhere.
10. **Secrets only from env.** Don't read or print `.env` files (permissions deny it); document every variable in `.env.example`.
11. **Migrations:** never edit an applied migration; destructive data migrations need a documented backup step.
12. **Tests:** don't weaken, skip or delete tests to get green, and don't special-case code for tests. Fix the code, or record why in PROGRESS.md.
13. **No PHI to external AI/LLM services**; legacy `ai` endpoints stay disabled until a DPIA covers them (ADR-014).

## Git
- Commit straight to `main` (owner's choice, ADR-001). Small commits, Conventional Commit messages, footer `Refs: <feature-id>`.
- `make check` green before every commit. Never `--no-verify`, force-push, rebase pushed work or rewrite history. Never commit `.env*` (except `.env.example`), `data/`, database files, dumps, logs or PHI.
- Mechanical moves (`git mv`) in their own commits.
- Push `origin main` after each green commit. At phase end: annotated tag `phase-<n>-complete`, pushed.

## Working style
- Investigate before changing: read the code you'll touch, its tests and the referenced design section.
- Run independent reads/searches in parallel. For broad sweeps of the legacy code, use an Explore subagent and keep the main context for decisions and edits.
- Verify UI work in a real browser with Playwright before calling a feature done; check the screen against `docs/agent/DESIGN-SYSTEM.md`.
- State lives in files (PROGRESS.md, features.json, git), not in your memory of the conversation — so context compaction never loses work. Commit and update PROGRESS.md before long refactors.
- Prefer the simplest design that meets the acceptance criteria and the compliance register. Don't add features nobody asked for; do add the tests, audit and validation the design requires.

## When you're unsure
- Regulatory or external-API question → `docs/compliance/KENYA-REGULATORY-REGISTER.md` and `docs/integrations/`. If not covered, check the primary source (hie-docs.dha.go.ke, afyalink.dha.go.ke, kenyalaw.org, odpc.go.ke, the provider's developer portal) and record the finding with its URL in `docs/agent/DECISIONS.md` → Findings.
- Lasting technical choice → write an ADR in `DECISIONS.md`, then implement.
- Business decision only the owner can make (hosting, insurers, thresholds, vendor agreements) → add it to PROGRESS.md "Questions for owner" with options and a recommendation, continue with the default in DESIGN §20 or with other features, and mention it in your end-of-session summary.

## Docs index
| File | Use it for |
|---|---|
| `docs/agent/DESIGN.md` | architecture, modules, identifiers, patient journey, UAC, data protection, terminology, billing, reporting, NFRs, API conventions, legacy migration |
| `docs/agent/DESIGN-SYSTEM.md` | Flat 2.0 high-contrast light UI: tokens, type, components, layouts, keyboard, copy |
| `docs/agent/IMPLEMENTATION.md` | session protocol, git, toolchain, make targets, gates, testing, seeds, integration build order |
| `docs/agent/PHASE-1.md` · `PHASE-2.md` · `PHASE-3.md` | phase briefs: scope, order, exit criteria |
| `docs/agent/COMPLETION.md` | definition of done, acceptance scenarios E2E-01…16, evidence pack, go-live |
| `docs/agent/features.json` | the feature ledger |
| `docs/agent/DECISIONS.md` | ADRs and research findings |
| `docs/compliance/KENYA-REGULATORY-REGISTER.md` | requirement IDs `KE-*` with sources |
| `docs/integrations/INSURANCE.md` · `PAYMENTS.md` · `STORAGE.md` | SHA/SMART/Slade360; M-Pesa/banks/cards; local ↔ S3 storage |
| `docs/operations/CASH-HANDLING-SOP.md` | cash procedure the cashier features implement |
