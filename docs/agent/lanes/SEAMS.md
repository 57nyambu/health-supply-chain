# Seams between the lanes (ADR-024)

The points where Phase 2 and Phase 3 meet. Each seam has one owner who builds it; the other
lane codes against the contract below (with a fake of its own until the real thing is on
`main`). Changing a contract is an integration decision: propose it in your lane progress
file, don't just edit.

## 1. Lane registrations — `api/config/lanes/` (on `main`)

`phase2.py` / `phase3.py`: `INSTALLED_APPS`, `URLS` (`(prefix, urls module)`, prefixes under
`api/v1/`), `SEED_STEPS` (run after Phase 1's, Phase 2's before Phase 3's), `CELERY_BEAT_SCHEDULE`
(names start `p2-` / `p3-`), `ROLE_GRANTS` (`{role code: (permission codes…)}`, existing roles
only) and `settings(env)` (new settings; document each in the lane sections of `.env.example`
and `docs/operations/ENV.md`). `config/tests/test_lanes.py` checks them.

## 2. Domain events — `apps.core.events` (on `main`)

```python
from apps.core import events
events.emit("billing.invoice.finalized", aggregate=invoice, payload={"visit_id": str(visit.pk)})

@events.consumer("billing.invoice.finalized", name="insurance.prepare_claim")
def prepare_claim(event: OutboxEvent) -> None: ...   # idempotent: runs at least once
```

Rules: emit inside the service transaction; payload holds IDs, codes, enums and decimal
strings only (personal-data keys are refused); topic = `<app>.<aggregate>.<past-tense verb>`;
consumers register in their app's `AppConfig.ready()` (import a `consumers` module); never
rename a consumer (renaming re-delivers). Relay: `core-relay-outbox`, every minute.

Events Phase 2 **must emit** (Phase 3 consumes them):

| Topic | Payload | Phase 3 uses it to |
|---|---|---|
| `visits.visit.opened` | `visit_id`, `patient_id`, `visit_type` (`opd`/`emergency`/`inpatient`), `coverage_id` or null | start payer authorisation, ECCIF 24-hour clock |
| `visits.visit.closed` | `visit_id`, `outcome` | close the claim session |
| `billing.charge.posted` | `charge_id`, `visit_id`, `service_code`, `coverage_id` or null, `payer_amount`, `patient_amount` | incremental claim lines (SHA sessions) |
| `billing.charge.reversed` | `charge_id`, `visit_id` | remove claim lines |
| `billing.invoice.finalized` | `invoice_id`, `visit_id`, `party` (`patient`/`payer`), `coverage_id` or null, `total` | prepare and scrub the claim |
| `billing.credit_note.issued` | `credit_id`, `invoice_id`, `amount` (key names avoid words the personal-data check refuses, e.g. "note") | adjust the claim |
| `inpatient.admission.opened` / `.discharged` | `admission_id`, `visit_id` | per-diem claims, discharge summary attachment |
| `payments.payment.posted` | `payment_id`, `method`, `amount`, `invoice_ids` | reconciliation |

Events Phase 3 emits (Phase 2 may consume): `insurance.coverage.verified` (`coverage_id`,
`result`), `insurance.preauth.decided` (`preauth_id`, `visit_id`, `status`),
`insurance.claim.decided` (`claim_id`, `visit_id`, `status`, `approved_amount`),
`insurance.remittance.posted` (`remittance_id`, `amount`).

## 3. Read selectors Phase 2 provides for claims

Phase 3 reads clinical and financial facts only through these functions (no imports of
Phase 2 models in Phase 3 business logic). Phase 2 builds them with its features; until they
are on `main`, Phase 3 defines a `Protocol` with these signatures in `apps/insurance/seams.py`
and tests against a fake.

```python
# apps/visits/selectors.py
def visit_for_claim(visit_id) -> VisitForClaim
    # number, patient_id, facility_id, visit_type, opened_at, closed_at, coverage_id,
    # attending practitioners [(user_id, regulator, registration_number, puid)],
    # diagnoses [(icd11_code, title, primary: bool)], admission_id or None
# apps/billing/selectors.py
def claimable_lines(visit_id, coverage_id) -> list[ClaimableLine]
    # charge_id, service_code, description, quantity, unit_price (Decimal), amount (Decimal),
    # serviced_on, sha_interventions [codes], preauth_required (bool)
def invoice_for_party(visit_id, coverage_id) -> InvoiceSummary | None   # number, total, status
# apps/documents (Phase 1, exists): claim attachments are Document rows (category
# claim_form / discharge_summary / invoice_pdf), read through documents.services.
```

`billing.Service` carries `sha_interventions: list[str]` and `etims_item_code` (DESIGN §10).
Phase 3 imports the SHA tariff into its own tables and validates those codes; it does not
migrate billing.

## 4. Payer, scheme and cover — `apps.insurance` (on `main`, owned by Phase 3)

`Payer` → `Scheme` → `Coverage(patient, scheme, member_number encrypted, relationship,
valid_from/to, verification, active)`. Phase 2 uses `insurance.selectors.active_schemes()`,
`coverages_for(patient)`, `is_current(coverage)` and the API (`GET /api/v1/insurance/schemes/`,
`GET/POST /api/v1/insurance/coverages/`, `POST …/coverages/{id}/end/`). A visit stores a
`coverage` FK (null = cash / self-pay); price lists may be keyed by `Scheme`. Phase 3 adds
eligibility (it sets `Coverage.verification`), consent, pre-authorisation, claims and
remittances, and may add fields to these models; it never removes or renames the fields above.

## 5. Payments provider port (owned by Phase 2)

The `PaymentProvider` protocol in `docs/integrations/PAYMENTS.md` §1 ("The port"). Phase 2
builds it in `apps/payments/providers.py` with a registry
(`apps.payments.providers.register(provider)`), cash and M-Pesa, and documents it in its
lane progress file when delivered. Phase 3's `apps/banking` implements Jenga, Buni, Pesapal
and PDQ against it and registers them from `BankingConfig.ready()`. Before the port is on
`main`, Phase 3 builds the vendor clients, signature/IPN verification, fakes and contract
tests without importing `payments`.

## 6. Callbacks and IPNs — `apps.integrations.webhooks` (on `main`)

`POST /api/v1/hooks/<provider>/<token>/` stores each notification encrypted in
`WebhookInbox`, rejects failed verification, marks duplicates by the provider's reference and
answers at once; `process-webhooks` (every minute) calls the provider's handler. Register in
your app's `ready()`:

```python
webhooks.register("mpesa", verify=verify_fn, reference=reference_fn, handle=handle_fn)
```

Provider codes: Phase 2 `mpesa`; Phase 3 `sha`, `smart`, `slade360`, `jenga`, `buni`,
`pesapal`, `etims`. Handlers are idempotent and never post money from a callback alone
(query first, PAYMENTS.md §1).

## 7. Staff notifications — `apps.integrations.notify` (on `main`)

`notify_user(user, subject=…, message=…)` stores a notice; the `deliver-notifications` job
e-mails it (outbox, retried 48 h). Bodies never contain clinical details. Phase 2 uses it for
reminders' staff side; SMS to patients is P2-APP-01's channel work; P3-NOT-01 hardens both
after P2-APP-01 is on `main`.

## W. Web extension slots (files owned by Phase 3, rendered by Phase 2)

| Slot | File | Rendered by Phase 2 in | Props |
|---|---|---|---|
| W1 | `web/src/components/insurance/payer-eligibility.tsx` → `PayerEligibility` | visit opening, under the payer / cover choice | `patientId`, `coverageId`, `onStatusChange` |
| W2 | `web/src/components/banking/payment-methods.tsx` → `ExtraPaymentMethods` | cashier, next to cash and M-Pesa | `invoiceId`, `amountDue`, `onSettled` |

Phase 2 renders the slot even while it returns `null`; Phase 3 implements it without
changing the props (add optional props only). Emergency visits never wait on W1.
