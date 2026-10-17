# Phase 3 lane — progress log

Written only by the Phase 3 lane (docs/agent/lanes/README.md). Newest session on top.
The integration session copies the essentials into docs/agent/PROGRESS.md when it folds
the lane in.

## Current state
- **Branch:** `lane/phase-3` (created 2026-10-17 from `origin/main` `b16ec0b`, pushed)
- **Stage:** A (Phase 2 has delivered nothing to `main` yet; `phase-1-complete` does not exist)
- **Last delivery to main:** none yet — see Session log
- **Next:** deliver slice 1 to `main` once `make check` + `make e2e` + `make audit-verify` pass
  on the merged result (browser runs coordinated with the Phase 2 lane, see Requests R-P3-001);
  then eTIMS client and fake (P3-TAX-01 vendor part), manual claim pack (P3-PVT-03), fingerprint
  capture UI for W1, PDQ settlement import.

## Feature status (lane view)
| Feature | State | Notes |
|---|---|---|
| P3-INS-01 | in progress | Models (eligibility, consent, preauth, claims + lines/diagnoses/attachments/submissions/history, remittances), port + taxonomy, seam Protocols, contract suite over 4 fakes. Claims services arrive with P3-CLM-01 (stage B). |
| P3-SHA-01 | in progress | HIE client (single-flight token, 401 replay, facility headers), CR/HWR/facility registry adapters, eligibility snapshots, benefits, `import_sha_tariffs` with versioned synthetic tariff. Facility set-up screen wiring needs Phase 1's admin (R-P3-007). |
| P3-SHA-02 | in progress | OTP and fingerprint consent API; W1 slot fills OTP and member-code consent; fingerprint capture UI to do (needs the workstation hardware-service contract, GAP-HIE-011). |
| P3-PVT-01/02 | in progress | SMART and Slade360 scripted fakes pass the contract suite; real adapters need specs (GAP-SMART-001, GAP-SLADE-001). |
| P3-BNK-01/02, P3-CRD-01 | in progress (vendor part) | Jenga signing + IPN (Basic auth) + status query; Buni IPN signature + IP allowlist; Pesapal token/IPN/checkout/status; fakes and IPN test vectors. Port glue, W2, PDQ, refunds: stage B. |
| others | todo | |

## Deliveries to main
<!-- - YYYY-MM-DD `<sha>` — features … (make check, make e2e green on the merged result) -->

## Seams published / consumed
- Consumed: `apps.insurance` models (extended, nothing renamed), `apps.core.events` (emits
  `insurance.coverage.verified`), `apps.integrations.exchange` (all HIE calls logged).
- Published on the lane branch (for Phase 2 to read once delivered): `GET/POST
  /api/v1/insurance/coverages/{id}/eligibility/`, `GET …/benefits/`, consent API
  `/api/v1/insurance/consents/` — behind slot W1, so Phase 2 needs no code for them.
- `apps/insurance/seams.py`: the SEAMS §3 selectors as a Protocol with a fake; switches to
  `apps.visits.selectors`/`apps.billing.selectors` automatically when they exist.

## Requests to integrator
- R-P3-001 — `web/playwright.config.ts` uses fixed ports (API 8000/8001, web 3100) with
  `reuseExistingServer: true`. With three checkouts on one machine, a lane's `make e2e` can
  silently run against another lane's API server. Please make the ports configurable
  (e.g. `E2E_API_PORT`, `E2E_WEB_PORT`) or turn reuse off by default.
- R-P3-002 — a `patients` service to link a registry identifier with source `client_registry`
  (e.g. `link_registry_id(patient, cr_id, actor)`), and a selector returning a patient's active
  identifiers by type. Until then eligibility stores the CR ID on `Coverage.payer_member_ref`
  (ADR-074) and `apps/insurance/refs.py` reads `PatientIdentifier` directly (read only).
- R-P3-003 — `docs/operations/ENV.md` lines for `HWR_MODE` and `CLIENT_REGISTRY_MODE` still say
  only `fake` exists; `sandbox`/`live` now use the HIE adapters with the `SHA_*` credentials.
- R-P3-004 — set `httpx`/`httpcore` loggers to WARNING in `LOGGING` (now done in
  `InteropConfig.ready()`); request lines carry identification numbers.
- R-P3-005 — Phase 1 tests `test_only_the_fake_exists_until_phase_3` (patients) and
  `test_only_the_fake_registry_exists_until_phase_3` (accounts) still pass (no credentials →
  refuse, naming the gap) but their names are now out of date.
- R-P3-006 — `api/CLAUDE.md` names `core.money` helpers that do not exist yet.
- R-P3-007 — facility set-up (Phase 1 admin) could call `GET /api/v1/interop/facility-registry/?identifier=&type=fid`
  to confirm the FID, KEPH level and SHA contract before saving (P3-SHA-01 acceptance 2, "facility setup").
- R-P3-008 — the `insurance` app's mypy strictness is set in a Phase 3 override block of `api/pyproject.toml`
  (apps.insurance, interop, banking, etims, privacy); fold it into the shared strict list when convenient.

## Questions for owner
<!-- - [Q-P3-001] question — options — recommendation — default used meanwhile -->
- none yet (DESIGN §20 defaults in use: SMART and Slade360 for private insurers; Pesapal for cards; eTIMS adapter built, flag off).

## Spec gaps
- [GAP-HIE-001] SHA/HIE — UAT client ID/secret, facility FR code — fake HIE meanwhile — owner action: request UAT credentials from the HIE integration team.
- [GAP-HIE-002…010] SHA/HIE — see `docs/integrations/sha-hie/SPEC-NOTES.md` (not-found shape, CR ID field, Maisha Namba type, PUID field, status vocabularies, trace header, OTP error words, ECCIF listing, unanswered visit creation) — conservative assumptions in `apps/interop/hie/mapping.py` and the SHA adapter — risk: UAT shows different values — confirm in UAT and record fixtures.
- [GAP-SMART-001] SMART — no API spec — scripted fake with the INSURANCE.md §5 capability outline — owner action: provider integration agreement, spec, test credentials.
- [GAP-SLADE-001] Slade360 — no API spec — scripted fake with the §6 outline — owner action: partner agreement, spec, test credentials.
- [GAP-HIE-011] SHA biometrics — the local fingerprint hardware service (`http://localhost:18065/status`, `workStationId`) is described only in prose — UI path not built — risk: none until a facility uses fingerprints — owner action: DHA biometrics onboarding for the facility.
- [GAP-SHA-TARIFF-001] SHA tariffs — the official Benefits and Tariffs spreadsheet and its column layout — synthetic `SYN-…` version loaded; importer reads our documented CSV layout — owner action: provide the spreadsheet.
- [GAP-JENGA-002/003] Jenga — token endpoint not in the public guides; decimal formatting in signed strings — sandbox/live refuse — owner action: JengaHQ onboarding, then record the token call from the portal or sandbox.
- [GAP-BUNI-001] KCB Buni — IPN payload, acknowledgement and query API only inside the Buni portal — IPNs verified (signature + IP) and stored, not confirmed — owner action: KCB request letter and portal access.
- [GAP-PESAPAL-001/002] Pesapal — IPN parameters/acknowledgement body; meaning of status 0 (INVALID) — read `OrderTrackingId`, treat 0 as pending — owner action: Pesapal sandbox account to record traffic.

## Waivers needed (vendor live verification)
- None requested yet; P3-PVT-01/02 will be `blocked` with "external: SMART/Slade360 spec and credentials" when their fake parts are complete.

## Synthetic data and scripted outcomes (demo every path)
- **Fake HIE** (`SHA_MODE=fake`, `apps/interop/hie/fake.py`) — by the last two digits of the national ID
  (or the ID inside `CR-SYN-N<id>`): 97 not found · 96 not eligible · 98 suspended (inactive, "contributions in
  arrears") · 95 timeout · `99999999` outage · 94 no confirmed phone (no OTP) · 93 fingerprint never matches ·
  92 no usable fingerprints → OTP allowed · 91 stuck PENDING authorisation · 90 facility enforces biometrics ·
  anything else eligible for SHIF and UHC this year. OTP `123456` good, `000000` wrong, `111111` expired.
  Interventions `SYN-SHA-OP-001…003`, `SYN-SHA-IP-001…003` (IP-001 per diem with no published rate),
  `SYN-PHC-001` (capitation), `SYN-ECC-001` (ECCIF). Practitioners `TEST-`/`EXPIRED-`/`SUSP-`; facilities `FID-SYN-…`
  (ending 9 = SHA contract suspended).
- **Banks and cards** (`apps/banking/fakes.py`) — Jenga transactions registered in the fake are confirmed by the
  status query (a different amount → `mismatch`, an unregistered reference → `unknown`); Buni IPNs are signed with a
  per-process test key (tampered body → rejected); Pesapal orders by cents: .00 completed · .02 failed · .03 reversed ·
  .04 still pending.
- **SHA tariff** — version `SYN-2026-10` (8 `SYN-…` interventions; `SYN-SHA-IP-001` has no published rate).
- **SMART / Slade360 fakes** (`apps/insurance/adapters/scripted.py`) — members by last two digits (97, 96, 98, 95
  as above); SMART member code `1234` / `0000` / `1111`; pre-authorisations and claims by cents: .00 approved ·
  .11 partially approved (90 %) · .22 declined/rejected (SYN-P01/SYN-R01) · .33 queried (SYN-Q01) · .44 pending ·
  .99 outcome unknown (payer has it) · .98 outcome unknown (payer never got it); approved claims are paid on the
  next remittance download.

## Session log

### 2026-10-17 — session 1 (setup, stage A start)
- Created `lane/phase-3`; local PostgreSQL cluster on 5433 with database `afyasync_p3` (Phase 2 uses
  `afyasync_p2`); pytest needs a private `--basetemp` here (the shared `pytest-of-xc` is locked by another session).
  Baseline on `origin/main`: 553 API tests passed.
- Read the HIE's published OpenAPI specs (auth, registries, eClaims, consent) and recorded the fields we use
  (DECISIONS findings, `docs/integrations/sha-hie/SPEC-NOTES.md`).
- Built: payer port + taxonomy (ADR-070), seam Protocols (ADR-071), HIE client + fake HIE (ADR-072), scripted
  outcomes (ADR-073), Coverage member reference (ADR-074); models for eligibility, consent, preauth, claims,
  submissions, status history, remittances (migration `insurance.0002`); SHA, SMART, Slade360 and manual
  adapters; contract suite (61 cases + 3 pending for SHA dispatch); real HIE registry adapters; eligibility
  and consent services and API; facility-registry endpoint.
- Then: SHA tariff versions + `import_sha_tariffs` (+ synthetic file and lane seed step `apps.insurance.seed_phase3`
  with scripted demo cover); W1 `PayerEligibility` (eligibility + OTP/member-code consent) and a claims-workspace
  "Cover check" page with a Playwright path (`web/tests/e2e/phase3/cover-check.spec.ts`); `apps.banking` (ADR-075).
- Found by the gate: `ClaimDiagnosis` now carries a sensitivity flag (Phase 1's sensitivity test); payer-calling
  actions check the Idempotency-Key after the policy so anonymous callers get 401/403.
- Coordinated browser runs with the Phase 2 lane (fixed e2e ports; both lanes' 16:28–16:40 runs were cross-wired and discarded).
