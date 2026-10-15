# Completion Guide — Definition of Done, Acceptance, Go-Live

## 1. Definition of done

**Feature** — every acceptance item in `features.json` verified end to end in the session that flips it; tests at the right layers (IMPLEMENTATION §7); API documented; permissions declared and in the role matrix; audit events written; UI keyboard path and axe clean; docs/SOPs/env examples updated; `make check` green; committed and pushed.

**Phase** — every feature of the phase passes; the phase's scenarios in §2 pass (`[P3]` steps pending in Phase 2); exit criteria in the phase brief met; PROGRESS.md summary written; annotated tag pushed.

**Project** — all scenarios pass with no pending steps (vendor-blocked steps run against fakes and are listed as external dependencies); traceability complete; evidence pack complete (§6); go-live runbook rehearsed on staging (§7); FINAL-REPORT.md written.

## 2. Acceptance scenarios

Each scenario is one Playwright spec in `web/tests/e2e/scenarios/` named after its ID, running against seeded synthetic data and fake integrations (sandbox where available with `RUN_LIVE=1`). Every page visited is checked with axe. Each spec also asserts the side effects listed under "Verify".

| ID | Scenario | Phase |
|---|---|---|
| E2E-01 | Adult cash OPD, reception to closed visit | 2 |
| E2E-02 | Child OPD with ETAT+ priority, returning patient; paid by cash (P2) then card (P3) | 2/3 |
| E2E-03 | SHA primary care (UHC capitation) visit with zero-total claim | 3 |
| E2E-04 | Unidentified emergency casualty, treated without payment, later identified; ECCIF claim inside 24 h [P3] | 2/3 |
| E2E-05 | Inpatient admission to discharge — cash variant (P2), SHA SHIF per-diem variant (P3) | 2/3 |
| E2E-06 | Inpatient with deposit, interim bill, waiver, discharge with balance → debt agreement; later M-Pesa C2B payment auto-matched | 2 |
| E2E-07 | Private insurer via SMART: member verification, preauth for imaging, claim, remittance, reconciliation | 3 |
| E2E-08 | Private insurer via Slade360: eligibility, claim rejected, corrected, resubmitted, paid | 3 |
| E2E-09 | Bank payments: Equity IPN auto-allocates; KCB STK succeeds; unmatched credit → suspense → approved allocation | 3 |
| E2E-10 | Refunds: cash (approval by a different user), M-Pesa reversal path, card refund | 3 |
| E2E-11 | Access control and break-glass | 1 |
| E2E-12 | Storage switch and migration (local ↔ S3) | 1 |
| E2E-13 | Cashier shift with mixed methods, variance, sign-off, Z-report | 2 |
| E2E-14 | Monthly MOH 705A/705B/717/706 from a fixture month | 2 |
| E2E-15 | Audit tamper detection | 1 |
| E2E-16 | HIE outage: care continues, eligibility pending, claims queued, recovery drains the queue | 3 |

### E2E-01 Adult cash OPD
1. Receptionist presses `/`, searches by phone, finds no match, registers a new adult with national ID, next of kin, privacy notice acknowledged.
2. Opens an OPD visit to consultation room 2 with payer cash; ticket printed.
3. Cashier receives the consultation fee in cash; receipt printed.
4. Triage nurse records vitals; system suggests yellow; nurse confirms.
5. Clinical officer calls the ticket, writes a SOAP note, records provisional ICD-11 diagnosis, orders a full blood count.
6. Cashier sends an M-Pesa STK prompt (fake success); payment confirmed by query; receipt sent by SMS without clinical details.
7. Lab collects the specimen (barcode), enters results, supervisor validates and releases; clinician sees the result.
8. Clinician finalises the diagnosis, prescribes two drugs; pharmacist verifies; cashier receives payment; pharmacy dispenses (FEFO batch chosen).
9. Clinician records disposition "home" with a follow-up appointment.
10. Visit becomes clinically complete → financially cleared → closed.
**Verify:** journey rail at each step; charges posted for consultation, lab, drugs; invoice and receipts numbered; stock decreased on the right batches; audit events for every chart open and write; MOH 705B count includes the final diagnosis.

### E2E-02 Child OPD, ETAT+
Returning 3-year-old found by MRN; ETAT+ "Priority" pushes the ticket ahead of earlier non-urgent tickets; consultation and pharmacy as E2E-01. Payment: cash in Phase 2; Pesapal card checkout (fake) in Phase 3.
**Verify:** queue ordering; MOH 705A (under 5) count; banner shows age in years and months.

### E2E-03 SHA UHC capitation [P3]
1. Reception searches by national ID → Client Registry match (CR ID) → eligibility shows UHC/PHC active → interventions loaded.
2. OTP consent: masked contact confirmed, OTP sent, entered; visit opened with consent token stored encrypted.
3. Consultation, lab, dispensing as normal; charges flagged payer-responsible.
4. Claim scrubbed (ICD-11 present, interventions mapped, documents attached), submitted with zero total; status moves to approved (fake).
**Verify:** no OTP or token in logs; ExchangeLog entries encrypted; claim states recorded; patient owes 0.

### E2E-04 Unidentified emergency
1. Ambulance arrival; quick registration as "Unknown male, approx. 30 years" with temporary ID; triage red.
2. Treatment, labs and drugs proceed with no payment, deposit or eligibility prompts at any service point.
3. [P3] ECCIF emergency claim opened at presentation; deadline alerts scheduled.
4. Patient identified next morning; HRIO requests merge with an existing record; supervisor approves.
5. [P3] Emergency claim updated with the identified patient and submitted before 24 h.
**Verify:** gate engine logged "emergency bypass" for each service; merge audited and reversible; 24-hour timer.

### E2E-05 Inpatient episode
1. Clinician requests admission; nurse assigns bed (double-booking attempt by a second user fails).
2. Two nights: ward rounds, MAR (one dose held with reason), observations; midnight job posts bed-days (re-run does not duplicate).
3. Discharge summary signed; discharge reason "recovered".
4. Cash variant (P2): final invoice, payment, bed to cleaning.
5. [P3] SHA SHIF per-diem variant: eligibility and consent at admission; per-diem allowance shown (unknown if unpublished); discharge via discharge OTP submits the claim; uncovered extras billed to the patient.
**Verify:** bed board states; MAR history; claim dispatch exactly once.

### E2E-06 Balance at discharge, no detention
Deposit taken at elective admission; interim bill; waiver requested by billing officer and approved by finance manager (self-approval attempt rejected); discharge with outstanding balance → debt agreement with two instalments; patient leaves (no blocking state). Weeks later an M-Pesa C2B payment with the invoice number as bill reference arrives → auto-matched and allocated.
**Verify:** no API or UI path blocks discharge; debt statement SMS has no clinical content; allocation audit trail.

### E2E-07 SMART [P3]
Member identified via SMART fake (card/code), benefits shown, preauth requested for an ultrasound and approved, service performed, claim posted with ICD codes per scheme, remittance received, matched to the payer invoice.

### E2E-08 Slade360 [P3]
Eligibility via Slade360 fake, claim submitted, rejected with reason "missing discharge summary", document attached, resubmitted, paid; aging report reflects the history.

### E2E-09 Banks [P3]
Equity IPN for a bill payment carrying the invoice number → payment posted after verification and allocated; KCB Buni STK push succeeds; an unmatched Buni IPN lands in suspense and is allocated after finance approval; daily reconciliation run shows all three correctly.

### E2E-10 Refunds [P3]
Cash refund requested by cashier, approved by finance manager, paid from an open shift; M-Pesa refund via reversal (fake); Pesapal card refund; each with receipts and audit.

### E2E-11 Access control
Receptionist can't open clinical notes (API 403, UI hides); clinician not on the care team sees summary only; break-glass with reason grants full access for 60 min with banner and notifications, then expires; expired licence blocks prescribing; privileged role grant waits for a second admin; DPO sees all of it in the audit viewer.

### E2E-12 Storage switch
Upload a lab PDF with `STORAGE_BACKEND=local`; switch to `s3` (MinIO); upload another; both download through the API; run `storage_migrate --from local --to s3 --verify`; all rows on S3; switch back to local; new uploads local, old still readable.

### E2E-13 Cashier shift
Open with counted float; receive cash, M-Pesa and (P3) card; one same-shift void approved by supervisor; safe drop; close with a KES 120 shortage → explanation required, finance notified; Z-report totals equal the ledger.

### E2E-14 MOH monthly reporting
Seed a fixture month; generate 705A, 705B, 717, 706; values equal the fixture's expected counts; DHIS2 payload validates against the mapping; unmapped ICD-11 codes appear in the HRIO report.

### E2E-15 Audit integrity
Perform audited actions; alter one audit row directly in the DB in the test; `make audit-verify` reports the exact break; restore and verify passes.

### E2E-16 HIE outage [P3]
Fake HIE returns timeouts: reception shows a banner and marks eligibility "pending verification"; care continues; claim operations queue; when the fake recovers, queued work drains in order and statuses update.

## 3. Traceability
`make traceability` collects `req("KE-…")` markers from pytest and Playwright annotations and writes `docs/generated/traceability.md`: requirement → tests → evidence files → status. Every `KE-*` ID must show at least one test or evidence item, or an explicit "external/owner" note with the reason.

## 4. Security checklist (summary — full ASVS L2 evidence in `docs/evidence/asvs-l2.md`)
- Default deny on every endpoint; policy matrix test green.
- MFA for privileged roles; lockout; session timeouts; workstation lock.
- No PHI in logs, URLs, error messages, notifications, analytics; scrubbing tests green.
- Field encryption and key rotation tested; document envelope encryption tested.
- CSP with nonces, HSTS, frame-ancestors none, no-referrer; cookies Secure/HttpOnly/SameSite.
- CSRF on all unsafe methods; CORS off (same origin).
- Rate limits: login, PIN, search, OTP, payment initiation.
- Webhooks verified (signature/basic auth/secret path + IP allowlist); raw payloads encrypted.
- Outbound host allowlist (SSRF guard).
- Containers non-root; Postgres/Redis not reachable from outside; firewall default deny; SSH key-only.
- Dependency, container and secret scans clean of high/critical.
- Audit chain verified daily; failure alerts.
- Breach workflow with 72-hour countdown tested with a drill.

## 5. Performance, resilience, backups
- Load test meets DESIGN §16 targets with 200k patients and 1M visits (report in `docs/evidence/perf.md`).
- Degraded-mode scenarios (E2E-16; payment provider down → alternative methods) pass.
- Backup job runs nightly; a full restore into a clean environment completed and timed (`docs/evidence/restore-drill-<date>.md`); RPO/RTO met.

## 6. DHA certification and data-protection evidence pack (`docs/evidence/`)
| Item | File | Register |
|---|---|---|
| Self-attestation inputs for the DHA HMIS form | `dha-self-attestation.md` | KE-DHA-01, KE-DHA-02 |
| ODPC registration checklist (controller per facility; processor for the vendor/host) | `odpc-registration.md` | KE-DPA-02 |
| Data inventory and record of processing | `data-inventory.md` | KE-DPA-01 |
| DPIA draft | `dpia.md` | KE-DPA-03 |
| Security, privacy and confidentiality policy | `security-privacy-policy.md` | KE-DHA-02 |
| Backup and recovery policy + latest drill | `backup-recovery-policy.md`, `restore-drill-*.md` | KE-DHA-02 |
| Interoperability statement (FHIR R4 resources, ICD-11, registries, HIE flows) | `interoperability.md` | KE-MOH-04, KE-DHA-04 |
| SHA UAT evidence (per checklist row) | `sha-uat/` | KE-DHA-03 |
| ASVS L2, threat model | `asvs-l2.md`, `threat-model.md` | KE-DPA-06 |
| Breach response runbook and drill | `../operations/BREACH-RESPONSE.md`, `breach-drill-*.md` | KE-DPA-04 |
The agent drafts these from the system's real configuration; the owner and the facility's DPO review and sign them. Nothing in the pack may claim a certification, registration or approval that has not happened.

## 7. Go-live runbook (rehearse on staging first)
1. **Hosting decision recorded** (ADR-006): production host and storage satisfy KE-DHA-06.
2. **Provision:** Ubuntu LTS host; SSH key-only; ufw default deny (allow 22 from admin IPs, 80/443); unattended security updates; Docker; no other apps on this host (patient data does not share a host with unrelated apps).
3. **Secrets:** production `.env` created on the host by the owner; keys generated fresh (Django secret, field encryption, storage master, blind index); stored in the owner's password manager; never in git or CI logs.
4. **Deploy:** Jenkins pipeline → build images → run migrations (after a pre-migration backup) → start → smoke tests (`/readyz`, login, open a workspace) → automatic rollback on failure.
5. **Facility setup:** facility registry data (MFL, FID, KEPH, KRA PIN, ODPC numbers), departments, service points, wards, beds, users and roles (MFA enrolment), price lists, SHA tariff import, payer configuration, DHIS2 mappings, receipt/invoice templates.
6. **Integrations to live,** one at a time, each with a small real transaction verified end to end: M-Pesa → Equity → KCB → Pesapal → SHA production (only after DHA certification) → private switches → eTIMS (if enabled).
7. **Data migration** from any legacy system: dry run on staging with a copy, reconciliation counts signed off, then production cut-over in a quiet window.
8. **Training** per role with the quick-reference guides; super-users per department.
9. **Parallel run** for the first days (paper backup forms available); downtime procedure printed at every service point.
10. **Hypercare** (two weeks): daily check of integration error rates, reconciliation, audit-verify, backups, open claim rejections; issue log.

## 8. Handover deliverables
Source on `main` with tags; `docs/` (design, ADRs, integration guides, SOPs, runbooks, evidence); role quick references; admin guide; API reference (OpenAPI + rendered docs); environment variable reference (`docs/operations/ENV.md`); seed and demo scripts; test reports; FINAL-REPORT.md.

## 9. External dependencies and owner actions (track in PROGRESS.md)
| Dependency | Needed for | Lead time |
|---|---|---|
| HIE UAT credentials, UAT demo booking, DHA certification | P3-SHA-*, go-live with SHA | weeks; SHA's HMIS deadline is already running |
| SHA Benefits and Tariffs spreadsheet (current version) | P3-SHA-01 | days |
| SHA callback URL configuration | P3-SHA-03, P3-SHA-07 | days |
| ODPC registrations (facility as controller; vendor/host as processor) | evidence pack, go-live | weeks |
| SMART and Slade360 integration agreements, specs, test credentials | P3-PVT-01/02 | weeks–months |
| Safaricom Daraja go-live (shortcode, passkey, initiator) | P2-PAY-03 live | days–weeks |
| Equity JengaHQ merchant onboarding; KCB Buni go-live letter | P3-BNK-* live | weeks |
| Pesapal merchant account | P3-CRD-01 live | days |
| KRA eTIMS integration approval (if system-to-system) | P3-TAX-01 live | weeks |
| Kenya-hosted production infrastructure (or ADR with legal basis) | go-live | days–weeks |

## 10. FINAL-REPORT.md (written by the agent at the end of Phase 3)
Sections: summary of what was built; scenario results; traceability summary; security and performance results; evidence pack index; known limitations; external dependencies still open with owner actions; recommended next steps (v1.1 backlog: WAL archiving for RPO 1 h, WebAuthn, patient portal, PACS viewer, LIS drivers, Swahili UI).
