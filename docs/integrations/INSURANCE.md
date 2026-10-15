# Insurance Integrations — SHA, SMART, Slade360 (+ M-TIBA, manual)

Required: **SHA plus at least two private insurance switches**. We build SHA (public), SMART and Slade360 (private switches that between them front most Kenyan private insurers). M-TIBA is an optional fourth adapter; the "manual" payer covers any insurer without an integration.

Status of specs (15 Oct 2026):

| Integration | Public spec? | What we have | Owner action needed |
|---|---|---|---|
| SHA via DHA HIE (eClaims REST) | Yes — hie-docs.dha.go.ke | Auth, registries, eligibility, consent, scenarios, dispatch, go-live process | UAT credentials from the HIE integration team; SHA tariff spreadsheet; facility FID |
| SHA via AfyaLink FHIR bundles | Yes — afyalink.dha.go.ke | Endpoints, checklist, reference PreAuth/Claim JSON | Access/secret keys; callback URL configured by payer team |
| SMART (Smart Applications International, MediSmart) | No — partner onboarding | Capability outline only | Provider integration agreement + API spec + test credentials |
| Slade360 (Savannah Informatics, EDI / HealthCloud) | No — partner onboarding | Capability outline only | Same |
| M-TIBA (CarePay) | No | Capability outline only | Optional |

**Rule:** never invent request or response fields. Build the port, the fake and the contract tests from this document; implement a vendor adapter only from the vendor's spec or recorded sandbox traffic. Log every unknown in PROGRESS.md under "Spec gaps".

---

## 1. Domain model (`apps/insurance`)

- `Payer` (SHA, insurer, employer) → `Scheme` (e.g. SHA: PHC/UHC, SHIF, ECCIF, POMSF; insurer corporate schemes) → `Coverage` (patient, scheme, member number, principal/dependant, valid from/to, verification state).
- `EligibilityCheck` — snapshot of every check (who, when, request hash, response summary, raw payload encrypted).
- `PayerConsent` — visit authorisation from a payer (SHA consent token, method OTP/biometric, expiry); token encrypted, redacted everywhere.
- `PreAuthorization` — requested items, diagnoses, doctors, attachments, status, approved amounts, expiry, payer reference.
- `Claim` (one per visit × payer coverage) → `ClaimLine` (from `billing.Charge`, payer code, quantity, unit price, net, serviced period, diagnoses) → `ClaimAttachment` (→ `documents.Document`) → `ClaimSubmission` (attempts, idempotency key, payload hash, response, outcome) → status history.
- `Remittance` / `RemittanceLine` — payer payments, allocated to claims and payer invoices.

The **local claim is the source of truth.** Adapters translate it; they never own business state.

## 2. The port

```python
class PayerGateway(Protocol):
    code: str                                   # "sha_hie", "sha_fhir", "smart", "slade360", "mtiba", "manual"
    def capabilities(self) -> PayerCapabilities: ...
    def find_member(self, query: MemberQuery) -> list[MemberMatch]: ...
    def check_eligibility(self, coverage: Coverage, on: date) -> EligibilityResult: ...
    def list_billable(self, coverage: Coverage) -> list[PayerServiceCode]: ...      # SHA interventions + flags
    def start_authorisation(self, coverage: Coverage, visit: Visit, codes: list[str],
                            method: AuthMethod) -> AuthChallenge: ...               # OTP sent / biometric iframe / card read
    def complete_authorisation(self, challenge: AuthChallenge, proof: AuthProof) -> PayerVisitHandle: ...
    def request_preauth(self, handle: PayerVisitHandle, preauth: PreAuthorization) -> PreauthRef: ...
    def preauth_status(self, ref: PreauthRef) -> PreauthStatus: ...
    def sync_claim(self, handle: PayerVisitHandle, claim: Claim) -> SyncReport: ...     # incremental payers push diffs; batch payers validate
    def submit_claim(self, handle: PayerVisitHandle, claim: Claim, idem_key: str) -> SubmitResult: ...  # exactly once
    def claim_status(self, ref: ClaimRef) -> PayerClaimStatus: ...
    def cancel_claim(self, handle: PayerVisitHandle, reason: CancelReason, text: str) -> None: ...
    def fetch_remittances(self, since: datetime) -> list[RemittanceAdvice]: ...
    def parse_callback(self, raw: WebhookInbox) -> PayerEvent: ...
```

`PayerCapabilities` flags: `incremental_claim_session`, `bundle_submission`, `consent_otp`, `consent_biometric`, `card_or_code_auth`, `preauth`, `remittance_api`, `callbacks`, `diagnosis_system` (`icd11` | `icd10` | per scheme).

Error taxonomy (shared): `ConfigurationError`, `ValidationRejected(violations)`, `BusinessRuleRejected(code, message)`, `AuthFailed`, `Forbidden`, `NotFound`, `RateLimited(retry_after)`, `TransientError`, **`SubmissionOutcomeUnknown`** (request sent, no reliable answer — never retry blindly; query status first).

A single **contract test suite** (`apps/insurance/tests/contract/`) runs against every adapter's fake, and against sandboxes when `RUN_LIVE=1` and credentials are present.

---

## 3. SHA — HIE eClaims REST (primary)

Source: hie-docs.dha.go.ke (Integration Scenarios, Auth, Registries, eClaims, Consent, Go-Live). Re-read those pages at the start of P3-SHA work; they were updated 28 Sept 2026.

### 3.1 Environments and auth
- UAT base: `https://ilm-dev.dha.go.ke/uat-middleware/api/v1`. Production base URL is issued with production credentials after DHA certification.
- `POST /tenants/token`, form-encoded `client_id`, `client_secret` → `access_token`, `expires_in`, `token_type`.
- Token cache per credential with single-flight refresh (one refresh for many concurrent callers) at 80% of lifetime; on 401, refresh once and replay once.
- Facility scoping: a facility-specific credential carries the facility in its token; a multi-facility credential sends the facility per request (`X-Facility-Id` + `X-Facility-Id-Type`, default type `fr-code`) — confirm on hie-docs "facility identification" before relying on it.
- Env: `SHA_MODE`, `SHA_BASE_URL`, `SHA_CLIENT_ID`, `SHA_CLIENT_SECRET`, `SHA_FACILITY_ID`, `SHA_FACILITY_ID_TYPE`, `SHA_CALLBACK_USER`, `SHA_CALLBACK_PASSWORD`, `SHA_CALLBACK_ALLOWED_IPS`.

### 3.2 Reception: identity, eligibility, billable interventions

| Step | Call | Use |
|---|---|---|
| 1 | `POST /tenants/token` | auth |
| 2 | `GET /patients` (`identification_number`, `identification_type`) | Client Registry match → CR ID (`patient_id`) + demographics to pre-fill registration |
| 3 | `GET /patients/eligibility` (same params) | Scheme statuses (SHIF, UHC, ECCIF, POMSF…) |
| 4 | `GET /patients/sub-benefits` (`patient_id`) | sub-benefit codes |
| 5 | `GET /patients/benefits/interventions` (`patient_id`, `sub_benefit_code`) | billable interventions with flags `paymentMechanism`, `needsPreauth`, `needsManualPreauthApproval`, `accessPoint` (OP/IP), `fund` |

Identification types on the HIE include National ID, Alien ID, Refugee ID (practitioners: registration number). Store the CR ID on the patient, and an `EligibilityCheck` snapshot per check. Intervention flags feed the payment-gate engine and the claim builder.

### 3.3 Consent (start of visit)
- **OTP:** `GET /patients/contacts` (masked numbers; confirm with the patient which one) → `POST /claims/otp` with `contact_id` → patient reads the code → `POST /claims/visit` with the OTP. A member with no confirmed phone cannot use OTP; offer biometrics or next-of-kin flows.
- **Biometrics:** `POST /claims/authorize` with biometric fields → response includes an iframe link where fingerprint matching happens → authorisation moves to `AUTHORIZED` (or `AUTHORIZED_PENDING_VISIT` for elective services) → `POST /claims/visit` with `auth_guid`.
- The `token` from authorisation/visit creation is the **consent token** used by every later call on the visit. Persist encrypted (`PayerConsent.token_encrypted`), never log it, never show it in the UI. A leftover `PENDING` biometric authorisation blocks the OTP path: list and reject it first.
- Never store OTP values; pass them straight through.

### 3.4 Scenarios

| Scenario | Fund | Access | Mechanism | Preauth | Dispatch |
|---|---|---|---|---|---|
| 1 SHIF IP per diem | SHIF | IP | per diem | no | discharge |
| 2 SHIF IP FFS normal preauth | SHIF | IP | fee for service | yes | discharge |
| 3 SHIF IP FFS elective preauth | SHIF | IP | fee for service | yes (elective) | discharge |
| 4 SHIF OP FFS elective preauth | SHIF | OP | fee for service | yes (elective) | submit |
| 5 SHIF OP FFS normal preauth | SHIF | OP | fee for service | yes | submit |
| 6 UHC OP capitation (PHC) | UHC | OP | capitation | n/a | submit (zero total) |
| 7 ECCIF emergency, identified | ECCIF | OP/IP | FFS / fixed | doctor consent | submit within 24 h |
| 8 ECCIF emergency, unidentified | ECCIF | OP/IP | FFS / fixed | doctor consent | submit within 24 h |

`insurance.services.classify_scenario(claim)` derives the scenario from coverage fund, visit type and intervention flags. Each scenario has its own pytest + Playwright path.

### 3.5 Building and dispatching the claim
The HIE keeps a server-side *virtual claim* per visit: you add interventions, diagnoses, billing lines, attachments and the attending doctor call by call, preview it, then dispatch. `sync_claim` diffs our `Claim` against the last known server state and applies only the needed operations; `ClaimSubmission` records each operation.

- Interventions: add / retire / switch as care changes. Elective scenarios use the pre-visit authorisation.
- Diagnoses: ICD-11 codes linked to the intervention they justify (KE-SHA-02).
- Billing lines: unit price, quantity, charge date, linked diagnoses, our charge ID as the service identifier (for reconciliation), practitioner.
- Attachments: claim form, itemised invoice, discharge/case summary are mandatory (KE-SHA-06); add lab results, imaging reports, preauth forms as required by the intervention's document rules. Keep each attachment within the documented size limit (observed limit ~10 MB — verify).
- Attending doctor: by regulator (KMPDC/COC/NCK) and registration number; verified against the Health Worker Registry.
- Preview before dispatch; translate server-reported blockers (missing lines, outstanding preauth, missing documents, no diagnosis) into our scrubber's messages.
- Dispatch: outpatient → `POST /claims/submit`; inpatient → discharge OTP (`POST /claims/otp/discharge`) or biometric re-authorisation → `POST /claims/discharge` (this submits the claim); discard → `POST /claims/close` with a cancel reason (`wrong_patient`, `no_service_given`, `wrong_benefit`, `expired_visit`, `exhausted_benefit`, `time_barred`, `other`).
- **Exactly once.** Submission/discharge are never auto-retried. On timeout or connection loss after sending, mark `SubmissionOutcomeUnknown`, preview/query the claim, and only resubmit if the server shows it unsubmitted.
- Observed UAT behaviours documented by a third-party SDK (`sha-claim` on PyPI, Apache-2.0, pre-production): outpatient submit also needed a discharge OTP and an attached doctor; per-diem tariffs may come back as zero when no KEPH-level rate is published. Treat these as hypotheses to verify in UAT, record what you observe in fixtures, and never coerce an unknown per-diem allowance to 0 (KE-SHA-08). Don't depend on that SDK without an ADR.

### 3.6 Pre-authorisation
- Normal vs elective (`needsManualPreauthApproval`) vs specialised (surgical, oncology, renal require additional data). Inputs: intervention, service window, items with estimated prices, diagnoses, doctors, notification email, attachments (preauth form, consultant request form, imaging/lab).
- States tracked locally from responses and status polls; doctor consent requests when the payer requires a doctor's approval.
- Gate: services flagged `needsPreauth` stay blocked until approval (except emergencies, which use ECCIF doctor consent).

### 3.7 Emergency (ECCIF)
- Open at presentation, identified or **unidentified** (no patient ID yet; record reason for unknown patient). Billed by approved emergency protocols with tariffs; doctor consent via OTP replaces preauth.
- **Submit within 24 hours.** `ClaimDeadline` with alerts at 12 h, 20 h and 23 h to the claims officer and shift in-charge.

### 3.8 Status and callbacks
- Claim states seen in SHA responses (from the AfyaLink checklist): `queued`, `approved`, `rejected`, `in-review`, `clinical-review`, `sent-for-payment-processing`, `sent-to-surveillance`, `payment-completed`, `payment-declined`. Store raw state + mapped internal state; unknown states are stored raw and flagged, never crash.
- Callbacks: POST to `/api/v1/hooks/sha/<token>/`, basic auth (+ IP allowlist), persisted raw then processed async. A poller (`sha_poll_claim_status`) covers missed callbacks.

### 3.9 UAT and certification (KE-DHA-03)
The HIE team's UAT checklist covers PHC (patient search, eligibility, capitation visit, intervention add/retire/switch, submit), SHIF (benefits and interventions, OP/IP visit with OTP, normal and specialised preauth, cancel preauth, submit with attachments, inpatient discharge) and ECCIF (emergency visit and claim). P3-SHA-08 turns each checklist row into an automated scenario that records screenshots and request/response logs into `docs/evidence/sha-uat/` (redacted).

## 4. SHA — AfyaLink FHIR bundle path (secondary, behind `SHA_TRANSPORT=fhir`)

Source: afyalink.dha.go.ke/claim-integration and the Kenya eClaims FHIR IG (draft). Keep it working because DHA publishes FHIR IGs as the national standard and certification asks for FHIR conformance.

- Pre-submission lookups: client registry (`/v3/client-registry/fetch-client`), facility search (`/v2/facility-search`), practitioner search (`/v1/practitioner-search`).
- Submit: `POST {base}/v1/shr-med/bundle` (FHIR `Bundle` of `type: message`, JSON). Status: `GET {base}/v1/shr-med/claim-status?bundle_id=` or `?claim_id=`. JWT auth. Status notifications by callback URL configured on AfyaLink (POST, basic auth, optional IP allowlist).
- Checklist rules to encode in the bundle builder and its validator:
  - every claim ID unique (resubmitting the same ID returns the previous response — idempotent);
  - `Insurance` and `Coverage` included; PFMS-eligible patients list both SHA and PFMS coverages, with an item extension pointing to the coverage each item belongs to;
  - terminology/system prefix per environment (production `https://fhir.sha.go.ke`; dev/UAT prefix as published);
  - every entry has a `fullUrl`; every reference resolves to an entry in the bundle;
  - `CareTeam` references a valid `Practitioner`;
  - `productOrService` is a valid SHA/PFMS intervention code; diagnoses use the ICD-11 system;
  - `total` = sum of item `net`; PHC claims total 0;
  - each item has `servicedPeriod.start/end` inside the claim `billablePeriod` (date-level), and its `sequence` aligns with that period; repeated intervention codes are allowed with unique sequences.
- Store AfyaLink's published reference PreAuth and Claim JSON as golden fixtures; the builder's output for the equivalent synthetic data must validate structurally against them (`fhir.resources` R4 + custom rules).

## 5. SMART (Smart Applications International)

What it is: the "Smart" member-access platform (smart cards, biometrics, mobile "smart code" authorisation) used by many Kenyan insurers — its site lists APA, AAR, Britam, CIC, First Assurance, GA, Heritage, ICEA, Jubilee, Kenyan Alliance, Madison, MUA and Old Mutual/UAP among clients. MediSmart integrates with hospital systems for benefit verification and electronic claims. Smart also sells its own DHA-certified HMIS (Smarthealth+, Sept 2026), so expect a partner agreement before API access.

Expected capabilities to confirm against the spec: member identification (card, biometric, member-generated code), benefits and balances, visit/session authorisation, pre-authorisation for some services, itemised invoice/claim posting with diagnoses, status and settlement information.

Build: `adapters/smart/` with `client.py` (transport), `mapping.py` (all field mapping in one place), `fake.py` (implements the capability set above with deterministic behaviour), and contract tests. Diagnosis code system per insurer may be ICD-10 — keep the ICD-11 → ICD-10 `ConceptMap` available and choose per scheme.

## 6. Slade360 (Savannah Informatics)

What it is: Slade360 EDI exchanges member eligibility from payers to providers, electronic claims from providers to payers, and remittance/workflow visibility back; HealthCloud exposes APIs for providers and developers. Savannah reports ~65% share of e-claims across five insurers plus SHA, and its Slade360 HMIS (with Safaricom) is DHA-certified. Slade codes already appear in SHA's FHIR samples as practitioner and facility identifiers — store `slade_code` on `Facility` and `ProfessionalLicence`.

Expected capabilities to confirm: eligibility and benefits, pre-authorisation, claim submission with invoice lines, claim workflow states (submitted, approved, rejected, paid), remittances.

Build exactly like SMART: client, mapping, fake, contract tests; real adapter only from the spec.

## 7. Optional: M-TIBA (CarePay)

Health wallet plus insurer administration platform (Safaricom, CarePay, PharmAccess) with thousands of contracted providers. Provider integration covers member verification, treatment authorisation and claims, with wallet payments. Build only if a client facility needs it; same pattern.

## 8. Manual payer

For insurers with no integration: generate a **claim pack** (ZIP) containing the invoice PDF, claim form PDF, discharge/case summary, relevant results and preauth letter, plus a CSV of lines. Status changes and remittances are entered manually by the claims officer; remittance entry needs maker-checker.

## 9. Claims workbench (P3-CLM-01)

**Scrubber** (runs on every claim change; dispatch blocked while any error remains):
1. Coverage active on every service date.
2. Diagnoses valid in the payer's code system (ICD-11 for SHA); at least one per intervention.
3. Every line mapped to a payer code that the facility is contracted for at its KEPH level.
4. Preauth present and approved where flagged; approved amounts not exceeded.
5. Mandatory documents attached (SHA: claim form, itemised invoice, discharge/case summary).
6. Attending practitioner attached with active licence and PUID.
7. Service periods inside the billable period; length of stay consistent with bed-days.
8. Totals reconcile (sum of lines; PHC = 0).
9. No duplicate (same patient + payer code + overlapping dates on another open claim).
10. Emergency claims inside the 24-hour window.
11. Consent token present and not expired (SHA).

**Queues:** ready to submit; awaiting documents; awaiting preauth; submitted; in review; rejected (with payer reason and suggested fix); paid; short-paid.
**Resubmission:** correct lines (edit + resubmit where the payer supports it) with a reason; history preserved.
**Aging:** 0–30, 31–60, 61–90, 90+ days by payer and scheme.
**Remittance reconciliation:** match remittance advice to claims and bank receipts; allocate to payer invoices; short-payments go to an appeal or write-off decision (maker-checker).

## 10. Security and testing
- Consent tokens, OTPs and member numbers are secrets/PHI: encrypted at rest, redacted in logs and `ExchangeLog` headers/bodies.
- All payer traffic logged to `integrations.ExchangeLog` (encrypted body, correlation ID, duration, outcome, trace IDs returned by the payer — quote them when raising tickets with DHA/SHA).
- Fixtures are synthetic or sanitised UAT recordings; no real member data in the repo.
- Contract suite + scenario suite (`pytest -m sha`, `pytest -m payers`) must pass in `fake` mode in CI; sandbox runs are opt-in (`RUN_LIVE=1`).
