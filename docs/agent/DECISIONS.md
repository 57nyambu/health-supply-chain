# Architecture Decision Records

Append new ADRs at the end; never edit an accepted ADR — supersede it with a new one that references it. Template:

```
## ADR-NNN Title
Status: proposed | accepted | superseded by ADR-MMM   Date: YYYY-MM-DD
Context: why a decision is needed (link register IDs / sources).
Decision: what we do.
Consequences: what follows, good and bad; what would make us revisit.
```

Research notes (a fact checked against a primary source, with the URL and date) also go here under "Findings" at the bottom.

---

## ADR-001 Trunk-based development on `main`
Status: accepted (owner) · Date: 2026-10-15
Context: The owner wants each phase in its own session with all code committed to `main`.
Decision: Commit directly to `main`; `make check` before every commit; annotated tag `phase-n-complete` at each phase end; no force-push or history rewrite.
Consequences: `main` must stay green; work-in-progress hides behind feature flags; CI on every push is the safety net.

## ADR-002 Django 5.2 LTS
Status: accepted · Date: 2026-10-15
Context: The legacy app targets Django 4.2, which reached end of life on 7 April 2026. Supported lines in Oct 2026: 5.2 LTS (to April 2028), 6.0 (to April 2027), 6.1.
Decision: Upgrade to Django 5.2 LTS on Python 3.12+.
Consequences: Longest support window with the best third-party compatibility; revisit when 6.2 LTS ships (April 2027).

## ADR-003 Monorepo layout
Status: accepted · Date: 2026-10-15
Context: The owner asked for `api/` and `web/` separation.
Decision: `api/` (Django; legacy `root/` renamed `config/`), `web/` (Next.js), `infra/` (compose, nginx, Jenkins, backup scripts), `data/` (local object store, git-ignored), `docs/`. App names with migrations are not renamed.
Consequences: One repo, one history, one CI; moves done with `git mv` in separate commits.

## ADR-004 Next.js 16 for the web app
Status: accepted · Date: 2026-10-15
Context: The owner asked to move the frontend to Next.js. Next.js 16 is the active LTS line (released 21 Oct 2025); Next.js 15 support ends 21 Oct 2026.
Decision: Next.js 16 App Router, React 19, TypeScript strict, Tailwind CSS 4, Radix primitives wrapped as owned components, TanStack Query, generated OpenAPI client.
Consequences: Modern stack with a support runway; verify version-specific APIs (e.g. request interception file naming, caching defaults) against the installed version's docs.

## ADR-005 Session authentication over a same-origin `/api`
Status: accepted · Date: 2026-10-15
Context: Legacy DRF tokens never expire and would sit in browser storage; an HMIS on shared workstations needs server-controlled sessions.
Decision: Django sessions in httpOnly cookies with CSRF; Next.js and nginx route `/api/*` to Django so the browser sees one origin; DRF token auth removed for browsers; service accounts use hashed, scoped API keys.
Consequences: No CORS, simpler CSRF, server-side revocation; Next.js server components forward the session cookie when fetching.

## ADR-006 Data residency for production patient data
Status: **proposed — owner decision required** · Date: 2026-10-15
Context: Kenyan law expects health data for primary and secondary care to be stored/processed in Kenya, with transfers out only under prescribed conditions (KE-DHA-06, KE-DPA-07). Contabo's object storage regions are EU, US and Singapore; the owner's current servers are Contabo.
Decision (default until the owner decides): production PHI (database, documents, backups, logs that could contain identifiers) is hosted in Kenya. Contabo is used for development and staging with synthetic data. The residency guard runs `strict` in production with an allowlist of approved endpoints.
Consequences: The storage switch still supports Contabo (and any S3 endpoint); pointing production at a non-Kenyan endpoint requires a new ADR stating the legal basis, signed off by the owner and the facility DPO.

## ADR-007 Storage abstraction with per-object backend and envelope encryption
Status: accepted · Date: 2026-10-15
Context: Files must live under `data/` by default or in an S3-compatible bucket, switchable.
Decision: `documents.storage` with two named backends; each `Document` row records its backend; new writes go to `STORAGE_BACKEND`; `storage_migrate` moves objects; every object envelope-encrypted (AES-256-GCM); files served only through an authorised, audited stream.
Consequences: Switching is a config change with no downtime; migration is resumable; presigned URLs are not used.

## ADR-008 ICD-11 as the primary diagnosis code system
Status: accepted · Date: 2026-10-15
Context: SHA requires valid ICD-11 codes on all claims (KE-SHA-02); MOH 705 reporting uses condition categories; some private insurers may still use ICD-10.
Decision: Clinicians code in ICD-11 (WHO MMS release, versioned). ICD-10 and MOH 705 categories come from `ConceptMap` tables.
Consequences: One clinical vocabulary; maps maintained by the HRIO; per-scheme code system on private payers.

## ADR-009 SHA transport: HIE eClaims REST primary, AfyaLink FHIR bundles secondary
Status: accepted · Date: 2026-10-15
Context: DHA documents two paths: the HIE eClaims API (virtual claim per visit, consent tokens, scenarios, UAT checklist — hie-docs, updated Sept 2026) and FHIR bundle submission via AfyaLink (`/v1/shr-med/bundle`). Certification asks for FHIR conformance.
Decision: Build the HIE REST path first (it is what the UAT checklist exercises); keep a FHIR mapping layer and the AfyaLink transport behind `SHA_TRANSPORT=fhir`.
Consequences: Two adapters behind one port; the FHIR layer doubles as SHR export and DSAR export.

## ADR-010 Private insurance through SMART and Slade360
Status: accepted · Date: 2026-10-15
Context: The owner requires at least three insurance integrations including SHA. Most Kenyan private insurers are reached through switches: SMART (Smart Applications International / MediSmart) and Slade360 (Savannah Informatics EDI/HealthCloud). Neither publishes open API docs.
Decision: SHA + SMART + Slade360, plus a manual claim-pack payer; M-TIBA optional. Vendor adapters are built from vendor specs only; until then, fakes and contract tests.
Consequences: Owner must secure partner agreements; adapters may be blocked on external parties without blocking the rest of Phase 3.

## ADR-011 Banks and cards
Status: accepted · Date: 2026-10-15
Context: Two banks and cards required.
Decision: Equity Bank via Jenga API v3; KCB via Buni; online cards via Pesapal API 3.0 hosted checkout; counter cards via standalone bank PDQ terminals with settlement-file reconciliation.
Consequences: No card data handled by our servers (minimal PCI scope); bank statement imports power reconciliation.

## ADR-012 Money movement rules
Status: accepted · Date: 2026-10-15
Decision: Idempotency keys on every initiation; a payment is posted only after the provider confirms by query where a query API exists; money-moving or claim-submitting writes are never auto-retried — uncertainty is resolved by querying; duplicate notifications are deduplicated on provider reference.
Consequences: Slightly slower confirmation; no double charges or phantom payments.

## ADR-013 Emergencies are never gated; discharge is never blocked by balance
Status: accepted · Date: 2026-10-15
Context: Constitution Art. 43(2), Health Act ss. 7 and 12, court rulings against detention (KE-HLT-01, KE-HLT-02).
Decision: Gate engine bypasses every gate for emergency visits; there is no state or permission that holds a patient or body for payment; balances become invoices and debt agreements.
Consequences: Encoded as tests that must never be removed.

## ADR-014 No PHI to external AI services
Status: accepted · Date: 2026-10-15
Context: Legacy `ai` endpoints exist; health data is sensitive and localised (KE-DPA-01, KE-DHA-06).
Decision: `AI_FEATURES_ENABLED=false` by default; no PHI sent to external AI/LLM APIs; any future AI feature needs a DPIA, de-identified input or in-country processing, and an ADR.
Consequences: Some legacy AI functionality is unavailable until reviewed.

## ADR-015 Flat 2.0 high-contrast light design system
Status: accepted (owner) · Date: 2026-10-15
Decision: Light mode only; text contrast ≥ 7:1, UI boundaries and focus ≥ 3:1 (verified in CI); Atkinson Hyperlegible Next; depth only for overlays; journey rail as the signature element.
Consequences: Tokens are fixed; changes go through DESIGN-SYSTEM.md and the contrast check.

## ADR-016 Modular monolith with a transactional outbox
Status: accepted · Date: 2026-10-15
Decision: Django apps as bounded contexts calling each other's services; domain events written to `core.Outbox` in the same transaction and relayed by Celery to idempotent consumers.
Consequences: One deployable unit with reliable async integration; revisit only if a module needs independent scaling.

## ADR-017 Quality-gate baseline for legacy code
Status: accepted · Date: 2026-10-15
Context: `make check` enforces ≥ 85 % line coverage and mypy (IMPLEMENTATION §6). The legacy retail code had no tests; much of it is disabled (AI, ADR-014), scheduled for replacement (M-Pesa/SMS clients → Phase 2 adapters, sales receipts → payments, analytics → reporting) or rewritten behind default-deny policies in P1-UAC-03.
Decision: The gate applies from P1-OPS-01. Modules in that category are listed in `api/pyproject.toml` `[tool.coverage.run] omit` with the reason and the feature that removes them; mypy runs on everything with default settings, and new apps (`access`, `audit`, `facilities`, `patients`, `documents`) get the per-module strict flags. The list only shrinks: a feature that reworks a listed module removes its entry and adds tests in the same commit. P1-UAC-03 removes the legacy view and permission entries.
Consequences: The 85 % gate is meaningful for all new code from the first commit; legacy code that is about to change is not tested twice. Revisit if any entry is still listed at the end of Phase 2.

## ADR-018 Facility mapping and Phase 1 build order
Status: accepted · Date: 2026-10-15
Context: DESIGN §4 makes `facilities.Facility` 1:1 with `warehouses.Branch`, but the legacy dashboards (`facility_ops`, `WorkerProfile.warehouse`) treat `warehouses.Warehouse` as the "health facility". PHASE-1 lists UAC-02 (facility/department/ward-scoped assignments), UAC-10 and UAC-04 (all audited) before FAC-01 and AUD-01, which they depend on.
Decision: `Facility` follows DESIGN (1:1 with `Branch`); a warehouse belongs to the facility of its branch, so legacy warehouse-keyed data is scoped through `warehouse.branch.facility`. Build order inside Phase 1: UAC-01 → AUD-01 core (record, chain, anchors, verifier) → FAC-01 → UAC-10 → UAC-02 → UAC-03 → UAC-04…07 → DATA-01 → PAT-01 → UAC-08/09 and AUD-01 PHI-read logging → DATA-02, STO-*, PAT-02 → WEB-*. Acceptance criteria are unchanged.
Consequences: Every API added after UAC-03 is born under default deny; AUD-01 is flipped only when PHI-read logging exists (after PAT-01 and STO-01).

## ADR-019 Mapping legacy retail roles to HMIS roles
Status: accepted · Date: 2026-10-15
Context: Existing staff hold one of six legacy roles (`User.role`). Default deny (P1-UAC-03) means they would lose all access without role assignments.
Decision: A data migration assigns, in the facility of each user's WorkerProfile branch: ADMIN → system administrator + facility administrator; BRANCH_MANAGER → store keeper + report viewer; PROCUREMENT and WAREHOUSE → store keeper; CASHIER → cashier; REPORTER → report viewer. Privileged grants made by this migration skip the second approver once, because no approver exists before the first administrator; every later privileged grant uses maker-checker. Users without a profile get nothing. `User.role` stays for the legacy dashboards until P1-WEB-06 and no longer grants anything.
Consequences: Branch managers lose user management until a facility administrator grants it explicitly; the owner should review migrated administrators after deployment (listed in the access review report).

## ADR-020 Generated PDFs with ReportLab
Status: accepted · Date: 2026-10-16
Context: DSAR summaries now, and receipts, invoices, discharge summaries and referral letters later, need server-side PDFs. WeasyPrint needs Pango/GTK native libraries (heavy in the slim image, awkward on Windows dev machines); headless browsers are heavier still.
Decision: ReportLab (BSD) platypus layouts in `apps/<app>` code; generated files are stored through `documents.services.store_generated` like any other document (encrypted, audited, never public). Dynamic text placed in `Paragraph` markup is XML-escaped.
Consequences: Layout is code, not HTML templates; the design-system font can be embedded later (Atkinson Hyperlegible Next, P1-WEB-02) with a TTF registration.

## ADR-021 Sensitive categories in exports and DSAR copies
Status: accepted · Date: 2026-10-16
Context: DESIGN §8.1 excludes sensitive PHI from exports by default; KE-DPA-05 gives the data subject a right of access to all their data. The DPO, who runs DSARs, has no chart access (DESIGN §7.4).
Decision: DSAR exports and every other export show sensitive items as `hidden: sensitive` placeholders unless the person producing the export holds `clinical.record.read_sensitive` and asks for them (`include_sensitive`); the choice is audited. A complete copy for the data subject is therefore produced jointly (e.g. DPO with the medical superintendent), and the PDF tells the reader that protected items exist and how to receive them. DSAR copies are `dsar_export` documents readable only with `patients.dsar.read`, through the register.
Consequences: No silent omission — placeholders show that something was withheld; facilities must assign a sensitive-access holder to complete such requests within the deadline.

## ADR-022 Web toolchain versions and supply-chain gate
Status: accepted · Date: 2026-10-16
Context: P1-WEB-01 scaffolds `web/`. pnpm 11 refuses packages younger than its minimum release age unless they are excluded by hand; some newest releases were a day old. Next.js 16.4.1 fixes two critical unauthenticated RCEs (see Findings).
Decision: Pin exact versions in `web/package.json`; never add `minimumReleaseAgeExclude` entries — choose an older release instead, except when a security release must be taken (then record it here). Next.js / eslint-config-next 16.4.1 (security floor; 16.4.2 only backports Turbopack fixes), React 19.3, TypeScript 5.9 (openapi-typescript 7 requires 5.x), ESLint 10 (9.x is out of support), Tailwind 4.3, Vitest 5.0.4, Playwright 1.64. `unrs-resolver` build scripts stay disabled (`allowBuilds`). Node 22 LTS (>= 22.12) locally and in `web/Dockerfile`.
Consequences: Upgrades are deliberate PRs that re-run `make check`; `pnpm audit` in `make deps-audit` catches advisories between upgrades.

## ADR-023 Patient search terms travel in request bodies, not URLs
Status: accepted · Date: 2026-10-16
Context: Reception searches by name, national ID, phone or MRN. As `GET …/search/?q=` the term sat in the URL, and URLs are written to nginx's default access log (`$request`) and to Django's `django.request` records (the request repr) — PHI in logs, against the root non-negotiable. FHIR solves the same problem with `POST [base]/Patient/_search`.
Decision: `POST /api/v1/patients/search/` and `POST /api/v1/patients/registry-search/` take their terms as JSON; GET is refused. Logged request objects are reduced to method and path by the scrubbing filter. nginx logs with `afyasync_no_query` (`$uri`, never `$request`/`$args`). Search stays a read: audited with an HMAC of the term, rate-limited, never idempotency-keyed.
Consequences: Search calls need the CSRF token like any POST; caches never store search responses. Other list filters that could carry PHI follow the same rule (UUIDs and codes in URLs only).

---

## Findings
<!-- Format: YYYY-MM-DD — fact — source URL — impact -->
- 2026-10-15 — MinIO no longer publishes server images on Docker Hub (`minio/minio` returns "object not found"); `pgsty/minio` publishes maintained rebuilds (latest `RELEASE.2026-08-04T00-00-00Z`) — https://hub.docker.com/v2/repositories/minio/minio , https://hub.docker.com/r/pgsty/minio — dev/CI compose uses `pgsty/minio` for the S3-compatible test backend; production S3 is whatever Kenyan endpoint ADR-006 selects, never this image.
- 2026-10-16 — Data Protection (General) Regulations 2021 (Legal Notice 263) deadlines, read from the gazetted text: access within 7 days (reg. 9(4)); rectification within 14 days, refusal notified within 7 days (reg. 10(4)–(5)); portability within 30 days on payment of the prescribed fee, refusal notified within 7 days (reg. 11(3), (6)); erasure answered within 14 days (reg. 12(3)); objection and restriction within 14 days; indirect collection notified within 14 days — https://www.odpc.go.ke/wp-content/uploads/2024/03/THE-DATA-PROTECTION-GENERAL-REGULATIONS-2021-1.pdf — `apps/patients/dsar.py` `DUE_DAYS` uses calendar days from receipt; the register flags overdue requests. Whether "days" excludes public holidays is not stated; calendar days are the conservative reading.
- 2026-10-16 — Next.js 16.4.1 is a security release: critical unauthenticated RCE in `use cache` functions returning typed arrays (GHSA-673q-mjm6-r5xr), critical unauthenticated RCE in the Image Optimization API with SVG (GHSA-2464-fhr4-w9xw), high DoS via Server Actions (GHSA-p3m5-59mp-jv5r); 16.4.2 adds only Turbopack backports — https://github.com/vercel/next.js/releases/tag/v16.4.1 , https://github.com/vercel/next.js/releases/tag/v16.4.2 — `web/` pins 16.4.1 as the floor (ADR-022).
