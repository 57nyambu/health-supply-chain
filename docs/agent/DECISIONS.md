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

## ADR-024 Parallel build lanes for Phases 2 and 3
Status: accepted (owner decision) · Date: 2026-10-17
Context: The owner wants Phase 2 and Phase 3 built at the same time by two agents while the integration session finishes Phase 1 (the phases were planned one after another, each committed straight to `main`). SHA, private insurers, banks, cards and eTIMS still need specifications, agreements and credentials from the owner.
Decision: Two lane branches, `lane/phase-2` and `lane/phase-3`, each in its own worktree; ownership by app, route and file, and delivery to `main` only as a fast-forward of a fully gated branch that already contains `main` (`docs/agent/lanes/README.md`). Lanes register apps, URLs, seed steps, beat jobs, settings and role grants in `api/config/lanes/phase<N>.py` and admin tabs in `sections-phase<N>.ts`, never in the shared lists. Seams both lanes need were built first on `main` (`docs/agent/lanes/SEAMS.md`): the transactional outbox `apps.core.events` (ADR-016), the callback inbox `apps.integrations.webhooks`, the notification outbox, `apps.insurance` (`Payer`, `Scheme`, `Coverage` with synthetic data) and two web extension slots. Vendor integrations are built as port, fake, contract tests and full fake-mode flows with synthetic data; the real adapter waits for credentials (feature `blocked` with the owner's waiver, PHASE-3 exit criteria). Phase 2 and 3 may start before `phase-1-complete`; tags still come in order. ADR numbers: integration 024–039, Phase 2 lane 040–069, Phase 3 lane 070–099.
Consequences: `main` always equals a gated lane head and lane merges are mechanical (generated files regenerated, lockfiles re-added, merge migrations where two leaves meet). The integrator folds each lane's registrations into the shared files at its phase tag. Phase 3's claims, reconciliation and eTIMS hooks (stage B) wait for Phase 2's billing and payments on `main`.

## Phase 2 lane ADRs (ADR-040…069)
<!-- Written only by the Phase 2 lane. -->

## Phase 3 lane ADRs (ADR-070…099)
<!-- Written only by the Phase 3 lane. -->

## ADR-070 The payer port takes snapshots; one registry picks the adapter per mode
Status: accepted · Date: 2026-10-17
Context: INSURANCE.md §2 sketches `PayerGateway` with our models as arguments. Four payers (SHA, SMART, Slade360, manual) must behave alike, three of them without specs, and the local claim must stay the source of truth (DESIGN §11).
Decision: `apps/insurance/gateway.py` defines the port, its results and the shared error taxonomy (incl. `SubmissionOutcomeUnknown`, `Unsupported`). Adapters receive frozen snapshots (`CoverageRef`, `VisitRef`, `ClaimDraft`, `PreauthDraft`) built by services (`refs.py`) and never read or write our tables. Secrets travel as `Secret` (redacted `repr`). The port adds `pending_authorisations`, `authorisation_status`, `reject_authorisation`, `cancel_preauth` and `find_claim` (query by our key after an unknown outcome — we never received the payer's reference) to the §2 list. `apps.insurance.adapters.gateway_for(Payer.gateway)` builds the adapter for `SHA_MODE`/`SMART_MODE`/`SLADE360_MODE`; modes without a spec or credentials raise `ConfigurationError` naming the gap. One contract suite (`apps/insurance/tests/contract/`, `pytest -m payers`) runs against every fake.
Consequences: services never special-case a payer; a vendor spec arriving changes one adapter folder. Fakes are process singletons, so scripted state does not survive a restart (acceptable for demos).

## ADR-071 Phase 2's claim facts behind a Protocol that switches itself
Status: accepted · Date: 2026-10-17
Context: Claims need visits, diagnoses, practitioners and billable lines that Phase 2 builds (SEAMS §3); Phase 3 must not import Phase 2 models.
Decision: `apps/insurance/seams.py` declares the three selectors as a `ClinicalFacts` Protocol with frozen DTOs. `facts()` returns Phase 2's `apps.visits.selectors`/`apps.billing.selectors` as soon as they exist on the branch, otherwise an in-memory `FakeClinicalFacts`; tests can `use()` their own. Visits and charges are referenced by UUID (`visit_id`, `charge_id`), never by foreign key.
Consequences: Stage B needs no claims-code change when Phase 2 lands — only the fake falls away. If Phase 2's DTO shapes differ from SEAMS §3, the Protocol is the contract to reconcile.

## ADR-072 The HIE client and an HTTP-level fake HIE
Status: accepted · Date: 2026-10-17
Context: SHA, the Client Registry, the Health Worker Registry and the Facility Registry all sit behind the HIE (one token service, one facility-scoping rule). UAT credentials are an owner action.
Decision: `apps/interop/hie/client.py` is the single transport: token cache with single-flight refresh at 80 % of `expires_in`, one refresh-and-replay on 401, facility headers only when `SHA_CREDENTIAL_SCOPE=multi_facility` (DHA discourages sending both), retries with jitter for reads only, every POST unretried, write timeouts/5xx → `HieOutcomeUnknown`, every call in `ExchangeLog` with secrets and identifiers removed from the logged copy (and secret URL paths replaced). The fake HIE (`fake.py`) is an `httpx.MockTransport` serving the documented operations, so `SHA_MODE=fake` runs the real adapters, mapping and error handling. The registry adapters (`apps/patients/adapters/client_registry/hie.py`, `apps/accounts/adapters/hwr/hie.py`) use it for `CLIENT_REGISTRY_MODE`/`HWR_MODE=sandbox|live`; the Phase 1 domain fakes stay the default. `httpx`/`httpcore` loggers are held at WARNING (request lines carry IDs).
Consequences: UAT is a configuration change plus fixture recording; spec gaps (error words, status vocabularies, PUID field) are isolated in `mapping.py` and the adapters.

## ADR-073 Scripted synthetic outcomes
Status: accepted · Date: 2026-10-17
Context: The owner wants to demo every payer path before credentials arrive (GUIDE-PHASE-3 "Synthetic data").
Decision: Outcomes are chosen by visible conventions, documented in the fakes and the lane progress file: HIE identifiers by their last two digits (97 not found, 96 not eligible, 98 inactive, 95 timeout, 94 no phone, 93 fingerprint fails, 92 no fingerprints → OTP, 91 stuck pending, 90 biometrics enforced, `99999999` outage); OTPs `123456` / `000000` / `111111`; SMART codes `1234` / `0000` / `1111`; private-payer members by last two digits; pre-authorisations and claims by the cents of the amount (.00 approved, .11 partial 90 %, .22 declined/rejected, .33 queried, .44 pending, .99 outcome unknown but received, .98 outcome unknown and lost). All codes are `SYN-…`.
Consequences: Deterministic tests and demos; nothing resembles real SHA tariffs or members.

## ADR-074 The payer's member reference lives on Coverage
Status: accepted · Date: 2026-10-17
Context: SHA consent and claims need the member's Client Registry ID; eligibility returns it (`memberCrNumber`). Phase 3 may not change `apps.patients`, and its public `add_identifier` cannot record a registry-sourced CR ID.
Decision: `Coverage.payer_member_ref` (encrypted, additive field) holds the payer's reference; for SHA it is the CR ID, used when the patient has no CR identifier. A request to the integrator asks for a `patients` service that links a registry ID with source `client_registry`.
Consequences: the CR ID may exist on the cover before it exists on the patient; once the patients service exists, eligibility will also link it there.

## ADR-075 Bank and card notifications before the payments port
Status: accepted · Date: 2026-10-17
Context: Phase 2 owns the payments ledger and the `PaymentProvider` port (SEAMS §5), not yet on `main`. Jenga, Buni and Pesapal notifications must still be verified, stored, deduplicated and confirmed now (GUIDE-PHASE-3 stage A), and a notification alone must never move money (PAYMENTS.md §1).
Decision: `apps.banking` registers webhook providers `jenga` (path token + the Basic-auth credentials Jenga's IPN guide prescribes), `buni` (path token + `Signature` SHA256withRSA over the raw body + source-IP allowlist, PAYMENTS.md §5) and `pesapal` (path token; status always from `GetTransactionStatus`). The handler stores a `BankNotification` and asks the provider for the payment's status; only a matching answer sets `confirmed` (different amount → `mismatch`, unknown reference → `unknown`; Buni stays `received` until a statement matches, GAP-BUNI-001) and emits `banking.notification.confirmed`. Jenga request signatures (`signing.py`) follow the documented concatenations. Provider HTTP goes through one logged client; Decimal amounts are written as exact JSON numbers. Fakes are `httpx.MockTransport`s (Jenga, Pesapal) and a per-process RSA key (Buni). Stage B maps confirmed notifications onto Phase 2's port and ledger.
Consequences: no payment is posted in stage A; reconciliation (P3-REC-01) consumes the notifications. Jenga and Buni sandbox/live stay off until their gaps close.

---

## Findings
<!-- Format: YYYY-MM-DD — fact — source URL — impact -->
- 2026-10-15 — MinIO no longer publishes server images on Docker Hub (`minio/minio` returns "object not found"); `pgsty/minio` publishes maintained rebuilds (latest `RELEASE.2026-08-04T00-00-00Z`) — https://hub.docker.com/v2/repositories/minio/minio , https://hub.docker.com/r/pgsty/minio — dev/CI compose uses `pgsty/minio` for the S3-compatible test backend; production S3 is whatever Kenyan endpoint ADR-006 selects, never this image.
- 2026-10-16 — Data Protection (General) Regulations 2021 (Legal Notice 263) deadlines, read from the gazetted text: access within 7 days (reg. 9(4)); rectification within 14 days, refusal notified within 7 days (reg. 10(4)–(5)); portability within 30 days on payment of the prescribed fee, refusal notified within 7 days (reg. 11(3), (6)); erasure answered within 14 days (reg. 12(3)); objection and restriction within 14 days; indirect collection notified within 14 days — https://www.odpc.go.ke/wp-content/uploads/2024/03/THE-DATA-PROTECTION-GENERAL-REGULATIONS-2021-1.pdf — `apps/patients/dsar.py` `DUE_DAYS` uses calendar days from receipt; the register flags overdue requests. Whether "days" excludes public holidays is not stated; calendar days are the conservative reading.
- 2026-10-16 — Next.js 16.4.1 is a security release: critical unauthenticated RCE in `use cache` functions returning typed arrays (GHSA-673q-mjm6-r5xr), critical unauthenticated RCE in the Image Optimization API with SVG (GHSA-2464-fhr4-w9xw), high DoS via Server Actions (GHSA-p3m5-59mp-jv5r); 16.4.2 adds only Turbopack backports — https://github.com/vercel/next.js/releases/tag/v16.4.1 , https://github.com/vercel/next.js/releases/tag/v16.4.2 — `web/` pins 16.4.1 as the floor (ADR-022).

### Findings — Phase 2 lane
<!-- Written only by the Phase 2 lane. Format as above. -->

### Findings — Phase 3 lane
<!-- Written only by the Phase 3 lane. Format as above. -->
- 2026-10-17 — The HIE docs site (Zudoku) bundles its OpenAPI 3.1 specs as browser assets: `auth`, `consent`, `eClaims`, `hieRegistry`, `shr`, `terminology` (titles "HIE Registries" v1.0.0 etc.; server `https://ilm-dev.dha.go.ke/uat-middleware/api/v1`). Field names in our HIE adapter come from these specs, read as text (never executed) — https://hie-docs.dha.go.ke/catalog — every operation, parameter and schema the adapter uses is listed in `docs/integrations/sha-hie/SPEC-NOTES.md` with its schema name; re-read the specs before UAT (the docs changelog moves).
- 2026-10-17 — Auth: `POST /tenants/token`, form-encoded `client_id`, `client_secret` → `access_token`, `expires_in` (integer), `token_type`; errors are `{error, message}`; later calls use `Authorization: Bearer` (security scheme `BearerAuth`, JWT) — https://hie-docs.dha.go.ke/auth/authentication — `apps/interop/hie/client.py`.
- 2026-10-17 — Facility identification: headers `X-Facility-Id` + `X-Facility-Id-Type` (only `fr-code` supported, example `FID-47-115307-8`); facility-specific credentials carry `facility_id`/`facility_id_type` claims in the token and normally send no headers; headers override the token claim and both must be present or both are ignored; DHA discourages sending both — https://hie-docs.dha.go.ke/docs/authentication/process/facility-identification — the client sends the headers only when `SHA_CREDENTIAL_SCOPE=multi_facility` (ADR-072).
- 2026-10-17 — Client Registry: `GET /patients?identification_number=&identification_type=` with types `National ID`, `ClientRegistry ID`, `Birth Notification`, `Birth Certificate`, `Alien ID`, `Refugee ID`, `Mandate Number` (the shared enum also has `Temporary ID`); response schema `Member` (`id`, `first_name`, `middle_name`, `last_name`, `gender`, `date_of_birth`, `phone`, `identification_type`/`identification_number`, `other_identifications[]`, `dependants[]`, …). The spec does not say whether "not found" is a 404 or an empty body (GAP-HIE-002) — https://hie-docs.dha.go.ke/registries/client-registry — we treat 404 and a body without `id` as not found, and `id` as the CR ID (GAP-HIE-003 until UAT confirms). Maisha Namba has no HIE identification type (GAP-HIE-004).
- 2026-10-17 — Health Worker Registry: `GET /professionals?identification_number=&identification_type=registration_number&regulator=KMPDC|COC|NCK|PPB`; response `{message: {contacts, identifiers{client_registry_id,…}, licenses[{license_start, license_end, license_type, …}], membership{registration_id, is_active (integer), licensing_body, …}, professional_details}}`. No field is named PUID (GAP-HIE-005) — https://hie-docs.dha.go.ke/registries/health-worker-registry — we store `identifiers.client_registry_id` as the PUID until UAT shows otherwise.
- 2026-10-17 — Facility Registry: `GET /facilities/search?identifier=&identifier-type=mfl|license-number|fr-code|registration-number|fid&name=`; response `FacilitySummary` (`fidCode`, `frCode`, `officialName`, `kephLevel`, `facilityLicenseStatus`, `facilityLicenseEndDate`, `shaContractStatus`, `shaContractedServices[]`, `SHAOperationStatus{operationalStatus,…}`, …; `shaConstractStartDate`/`shaConstractEndDate` spelled so) — https://hie-docs.dha.go.ke/registries/facility-registry — used for the facility check (P3-SHA-01).
- 2026-10-17 — Eligibility: `GET /patients/eligibility?identification_number=&identification_type=` (default `ClientRegistry ID`) → `CoverageResult` (`memberCrNumber`, `statusCode`, `statusDesc`, `facilityBiometricsEnforced`, `whitelistedForOTP`, `isAlive`, `schemes[]{schemeId, schemeName, memberType, coverage{status, startDate, endDate, reason, message, possibleSolution}, policy{number, startDate, endDate}, principalContributor{…}}`); POMSF is matched by `schemeName` prefix `POMSF`. Values of `coverage.status` and `statusCode` are not enumerated (GAP-HIE-006) — https://hie-docs.dha.go.ke/eclaims/eligibility — the adapter treats status text `ACTIVE` (case-insensitive) as active and stores the raw text; UAT must confirm.
- 2026-10-17 — Benefits: `GET /patients/sub-benefits?patient_id=` → paged `{count, results[{code, name, fund, accessPoint, parentBenefitCode, status, active, cover{…}, …}]}`; `GET /patients/benefits/interventions?patient_id=&sub_benefit_code=` → paged `results[]` of `Intervention` (`code`, `name`, `fund`, `accessPoint`, `paymentMechanism`, `needsPreauth`, `needsManualPreauthApproval`, `needsDoctorAuthorization`, `kephLevelTarriff` (sic), `level2Tariff`…`level6Tariff`, `overallTariff`, `applicableDocumentTypes[]`, `requiredPreauthDocumentTypes[]`, …; all tariffs typed `number`) — https://hie-docs.dha.go.ke/eclaims/eligibility — tariffs are converted to `Decimal` from their JSON text; a missing tariff stays `None`, never 0 (KE-SHA-08).
- 2026-10-17 — Consent: `GET /patients/contacts?patient_id=` → `{count, results[{id (integer), contactType, contactValue (masked), isConfirmed, active}]}`; `POST /claims/otp` `{patient_id, intervention_codes[], contact_id?}` → `{message, data{…}}`; `POST /claims/authorize` (OTP variant `{patient_id, service_type OUTPATIENT|INPATIENT, otp, interventions[]}`; biometrics variant requires `agent_id`, `authorizing_device_os` windows|android, `ekyc_provider_id`, `factors[]`, `interventions[]`, `is_biometrics_discharge_authorization`, `is_emergency`, `is_integration`, `patient_id`, `provider` (FR code), `service_type`, `work_station_id`) → `Authorization` (`guid`, `status`, `token`, `authorizationReason`, `shaVerificationRequest{requestUrl, embededToken, embedExpiry}`, …); `GET /claims/authorizations?token=|guid=|patient_id=` → list; `POST /claims/authorizations/{consent_token}/reject` (no body). Statuses `PENDING`, `AUTHORIZED`, `AUTHORIZED_PENDING_VISIT`, `REJECTED`; `REJECTED` with `authorizationReason=BIOMETRICS_NOT_FOUND_OTP_ALLOWED` means use OTP. The biometric iframe expires after 10 minutes and allows 3 attempts; a stuck `PENDING` authorisation blocks a new one for the same context — https://hie-docs.dha.go.ke/docs/consent/process/getAuthorizations , https://hie-docs.dha.go.ke/docs/consent/process/rejectAuthorization , https://hie-docs.dha.go.ke/docs/consent/process/biometricsConsent — consent flows in `apps/insurance/adapters/sha_hie/`.
- 2026-10-17 — Start visit: `POST /claims/visit` is `oneOf` OTP `{intervention_codes[], patient_id, service_type CAPITATION|OUTPATIENT|INPATIENT|EMERGENCY, otp}`, biometrics `{…, auth_guid}`, minors `{…, match_id}`, each with optional `practitioner_identification_type`/`_number`/`practitioner_regulation_body`; response `ClaimAuthorization` (`authorization_code`, `visit_number`, `workflow_state`, `claim_id`, …). "The authorization_code returned in the Start Visit response is the consent_token used by subsequent API calls" — https://hie-docs.dha.go.ke/docs/claims/process/startVisitConsent/startVisitWorkflow , https://hie-docs.dha.go.ke/eclaims/start-visit-consent — stored encrypted as `PayerConsent.token_encrypted`. INSURANCE.md §3.3's "`POST /claims/visit` with the OTP" matches; the OTP itself is never stored. How later calls carry the token (header or body) is per operation (read with P3-SHA-03).
- 2026-10-17 — Jenga request signing: RSA key pair (`openssl genrsa … 2048`), SHA-256 signature (PKCS#1 v1.5, per the PHP/Python samples), Base64 in the `Signature` header; documented concatenations: account balance `accountId+countryCode+date` (example `0011547896523KE2018-08-09`), create payment link `expiryDate+amount+currency+amountOption+externalRef` (example `2024-03-22+400+KES+OPEN+123456789`), transaction details `ref` — https://developer.jengahq.io/guides/get-started/generate-signature , https://developer.jengahq.io/api-explorer/receive-money/payment-link-as-api , https://developer.jengahq.io/api-explorer/receive-money-queries/query-transaction-details — `apps/banking/signing.py`. The token endpoint is not in the public guide pages read (GAP-JENGA-002); decimal formatting inside the concatenation is not documented (GAP-JENGA-003).
- 2026-10-17 — Jenga transaction status: `GET {uat.finserve.africa|api.finserve.africa}/v3-apis/transaction-api/v3.0/transactions/details/{ref}` → `{status, code, message, data{state, stateCode (2 success, 1 failed, -1 awaiting callback), amount, charge, transactionReference, serviceName, biller}}`; not found = `status:false`, code 111102. Payment link: `POST …/api-checkout/api/v1/create/payment-link` (`customers[]`, `paymentLink{expiryDate, saleDate, paymentLinkType, saleType, name, description, externalRef, amountOption, amount, currency}`) — same URLs — for the stage B glue.
- 2026-10-17 — Jenga IPN: POST JSON to the URL registered in JengaHQ with HTTP Basic credentials (no signature described); fields `callbackType`, `customer{name, mobileNumber, reference}`, `transaction{date, reference, paymentMode, amount, currency, billNumber, orderAmount, serviceCharge, status SUCCESS|FAILED, remarks}`, `bank{reference, transactionType, account}` (the field table says `bill` for the last two); acknowledgement and retries undocumented — https://developer.jengahq.io/guides/jenga-pgw/instant-payment-notifications — `apps/banking/notifications.py`.
- 2026-10-17 — Pesapal API 3.0: `POST /api/Auth/RequestToken` `{consumer_key, consumer_secret}` → `{token, expiryDate}` (about 5 minutes); `POST /api/URLSetup/RegisterIPN` `{url, ipn_notification_type}` → `ipn_id`; `POST /api/Transactions/SubmitOrderRequest` `{id ≤50, currency, amount, description ≤100, callback_url, notification_id, billing_address{email_address or phone_number, …}}` → `{order_tracking_id, merchant_reference, redirect_url}`; `GET /api/Transactions/GetTransactionStatus?orderTrackingId=` → `{payment_method, amount, confirmation_code, payment_status_description, status_code (0 INVALID, 1 COMPLETED, 2 FAILED, 3 REVERSED), merchant_reference, currency}`; callbacks and IPNs carry no payment status. Sandbox `https://cybqa.pesapal.com/pesapalv3`, live `https://pay.pesapal.com/v3` — https://developer.pesapal.com/how-to-integrate/e-commerce/api-30-json/authentication , …/registeripnurl , …/submitorderrequest , …/gettransactionstatus — `apps/banking/providers.py`. The IPN parameters and required acknowledgement body were not on the pages read (GAP-PESAPAL-001): we read `OrderTrackingId`/`OrderMerchantReference`, the names in the documented callback URL. Whether INVALID (0) means "not yet paid" is not stated (GAP-PESAPAL-002): treated as pending.
- 2026-10-17 — KCB Buni documentation is served only inside its developer portal (https://sandbox.buni.kcbgroup.com/devportal/apis shows nothing without sign-in); PAYMENTS.md §5 is our source for the IPN signature (GAP-BUNI-001) — https://buni.kcbgroup.com/ — Buni IPNs are verified and stored, not confirmed, until the spec is recorded.
- 2026-10-17 — The specs' error schema names (`gitlab_slade360emr_com_sha-edi_hie-middleware_…`) show the HIE middleware is built by Savannah Informatics (Slade360) — https://hie-docs.dha.go.ke/catalog — no impact on the design; noted for support tickets.
