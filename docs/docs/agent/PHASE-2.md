# Phase 2 — Clinical Journey, Billing Core, Cash and M-Pesa

**Goal:** a patient can be taken from reception to completion — OPD, emergency and inpatient — with triage, consultation (ICD-11), orders, lab, imaging, pharmacy with batch stock, procedures, admission and discharge; every service is charged automatically; bills are paid by cash or M-Pesa; MOH reports come out of the data. Insurance steps are stubbed with fakes and marked `[P3]`.

**Session:** a new Claude Code session. Start only if tag `phase-1-complete` exists. Commit to `main`; tag `phase-2-complete` at the end.

## Entry criteria
- `phase-1-complete` tag present; `make check` and `make e2e` green on `main`.
- PROGRESS.md Phase 1 summary read; open spec gaps and owner answers noted.

## Read first
DESIGN §6 (journey), §9 (terminology), §10 (billing), §12 (reporting), §14; `docs/integrations/PAYMENTS.md` §1–3; `docs/operations/CASH-HANDLING-SOP.md`; DESIGN-SYSTEM §6–9.

## Work order

| # | Features | Notes |
|---|---|---|
| 1 | P2-BIL-01, P2-VIS-01, P2-VIS-02, P2-VIS-03 | Catalogue and price lists first (gates need prices); then visits, queues, gates. Emergency and discharge "never gated" tests land with the gate engine. |
| 2 | P2-TRI-01, P2-CLI-01, P2-CLI-02, P2-CLI-03 | Triage scales are configuration; load the WHO ICD-11 release (download in a setup command, don't commit the full release if its licence forbids redistribution — check and record). |
| 3 | P2-BIL-02, P2-ORD-01 | Charge capture before orders so orders create provisional charges. |
| 4 | P2-LAB-01, P2-RAD-01, P2-NUR-01 | |
| 5 | P2-INV-01, P2-PHA-01, P2-PHA-02, P2-PHA-03 | Inventory upgrade must keep legacy inventory tests green. |
| 6 | P2-IPD-01, P2-IPD-02 | Bed-day job idempotent and re-runnable. |
| 7 | P2-BIL-03, P2-PAY-01, P2-BIL-04, P2-IPD-03 | Invoices → payments core → deposits/waivers/debts → discharge without detention. |
| 8 | P2-PAY-02, P2-PAY-03 | Cash per the SOP; M-Pesa adapter replaces legacy code. Run a Daraja sandbox session if credentials exist; record sanitised fixtures. |
| 9 | P2-REF-01, P2-APP-01, P2-REP-01 | Reports from data; DHIS2 mappings operator-maintained. |
| 10 | P2-WEB-01, P2-WEB-02, P2-WEB-03 | Workspaces can be built incrementally alongside the API features above — but the feature counts as done only when both API and UI acceptance pass. |
| 11 | P2-E2E-01 | Scenario suite; exit. |

## Design reminders
- `Visit.status` changes only through `visits.services` transitions.
- Clinical documents are signed then immutable; amendments are versions.
- Every stock movement is a ledger row; never edit quantities in place.
- Money: `Decimal`, explicit rounding, M-Pesa whole-shilling rule (PAYMENTS.md §2).
- No SMS/email body contains clinical information.
- A patient's outstanding balance never blocks discharge or release of records.

## Pitfalls to avoid
- Coupling clinical apps to billing models directly — use `billing.services.capture_charge` with events.
- Building per-payer logic into clinical code — payer rules live in gates and the billing responsibility split.
- Posting an M-Pesa payment from the callback alone — confirm by query.
- Treating seeded SHA interventions as real tariffs — they are synthetic until the real spreadsheet is imported in Phase 3.

## Exit criteria
- Every Phase 2 feature `passes: true`.
- E2E-01, E2E-02 (cash variant), E2E-04 (clinical part), E2E-05 (cash inpatient variant), E2E-06, E2E-13, E2E-14 pass; Phase 1 scenarios still pass; `[P3]` steps pending.
- A day-in-the-life demo script (`docs/evidence/phase-2-demo.md`) walks one OPD, one emergency and one inpatient patient through the system with screenshots.
- PROGRESS.md Phase 2 summary; tag `phase-2-complete` pushed.
