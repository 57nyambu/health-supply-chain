# Guide — Phase 2 lane (clinical journey, billing core, cash, M-Pesa)

You build Phase 2 (`docs/agent/PHASE-2.md`, the `P2-*` rows of `features.json`) on the branch
`lane/phase-2`, in parallel with the Phase 3 lane and the integration session (ADR-024).
Read `docs/agent/lanes/README.md` (how lanes work together) and `SEAMS.md` (contracts) first;
they override anything here that conflicts.

## Owner decisions behind this lane

- Phase 2 starts before `phase-1-complete` exists: Phase 1 is feature-complete on `main` and
  its scenarios (E2E-11/12/15) are green; only the Docker/Jenkins verification (PROGRESS.md
  Q-001) is outstanding. Treat `P1-E2E-01` as met for your features' `depends_on`.
- You tag `phase-2-complete` only after `phase-1-complete` exists (README §7).
- External systems you need (Daraja go-live, KHIS) may not have credentials yet: build
  port → fake → contract tests → full flows in fake mode, log spec gaps, and mark only the
  live step as an external dependency.

## First session

```bash
git fetch origin
git worktree add ../afyasync-phase-2 -b lane/phase-2 origin/main   # or reuse your checkout
cd ../afyasync-phase-2 && git push -u origin lane/phase-2
make setup && make seed && make check
```
(If `lane/phase-2` already exists on origin, check it out instead of creating it.) Then read
`CLAUDE.md`, `api/CLAUDE.md`, `web/CLAUDE.md`, PHASE-2.md, DESIGN §4, §6, §9, §10, §12, §14,
`docs/integrations/PAYMENTS.md` §1–3, `docs/operations/CASH-HANDLING-SOP.md`, DESIGN-SYSTEM
§6–9, and `docs/agent/lanes/PROGRESS-PHASE-2.md`.

## What you own

API apps `visits`, `clinical`, `terminology`, `orders`, `laboratory`, `imaging`, `pharmacy`,
`inpatient`, `referrals`, `billing`, `payments`, `reporting` (create them), the legacy
inventory apps (`products`, `warehouses`, `suppliers`, `procurement`, `sales`) and
`analytics`/`facility_ops` for reporting; additive changes to the Phase 1 apps. Web routes for
triage, consultation, lab, imaging, pharmacy, wards, cashier, billing, queue board, reports,
inventory, the clinical parts of `/patients/[id]` and visit opening at reception; the shared
UI kit (backward-compatible changes). Registrations go in `api/config/lanes/phase2.py`; admin
tabs in `web/src/app/(workspace)/admin/sections-phase2.ts`. Never edit Phase 3's files
(`apps/insurance`, `apps/banking`, `apps/interop`, `apps/etims`, `components/insurance/`,
`components/banking/`, `config/lanes/phase3.py`).

## Work order

Follow PHASE-2.md's order; deliver to `main` after each row (README §5).

| # | Features | Lane notes |
|---|---|---|
| 1 | P2-BIL-01, P2-VIS-01, P2-VIS-02, P2-VIS-03 | `billing.Service` gets `sha_interventions` and `etims_item_code`; price lists may be keyed by `insurance.Scheme`. A visit stores `coverage` (FK to `insurance.Coverage`, null = cash). Visit opening renders slot W1 (`PayerEligibility`). Emit `visits.visit.opened/closed`. Emergency and discharge "never gated" tests land with the gate engine. |
| 2 | P2-TRI-01, P2-CLI-01, P2-CLI-02, P2-CLI-03 | `terminology` holds ICD-11: check the WHO licence before committing release files (record the finding). Clinical sections plug into `patients.selectors.chart_sections` (access level and sensitivity already applied). |
| 3 | P2-BIL-02, P2-ORD-01 | `billing.services.capture_charge(event)` idempotent; emit `billing.charge.posted/reversed`. |
| 4 | P2-LAB-01, P2-RAD-01, P2-NUR-01 | |
| 5 | P2-INV-01, P2-PHA-01, P2-PHA-02, P2-PHA-03 | Keep legacy inventory tests green; ledger rows only. |
| 6 | P2-IPD-01, P2-IPD-02 | Emit `inpatient.admission.opened/discharged`. |
| 7 | P2-BIL-03, P2-PAY-01, P2-BIL-04, P2-IPD-03 | Emit `billing.invoice.finalized`, `billing.credit_note.issued`, `payments.payment.posted`. Publish the `PaymentProvider` port and registry (SEAMS §5) and the claim selectors (SEAMS §3) **as early as you can** — Phase 3 waits for them. Cashier renders slot W2 (`ExtraPaymentMethods`). |
| 8 | P2-PAY-02, P2-PAY-03 | Cash per the SOP; M-Pesa adapter replaces `apps/integrations/mpesa.py`; callbacks through `apps.integrations.webhooks` (provider `mpesa`); query before posting. Daraja sandbox only with credentials (owner action). |
| 9 | P2-REF-01, P2-APP-01, P2-REP-01 | MOH 705A/B, 717, 706 from data; extend `/reports` (it shows facility operations today). DHIS2/KHIS export behind a fake until credentials. |
| 10 | P2-WEB-01, P2-WEB-02, P2-WEB-03 | Build workspaces alongside the API features; drive `JourneyRail` from `Visit.status`. |
| 11 | P2-E2E-01 | E2E-01, E2E-02 (cash), E2E-04 (clinical part), E2E-05 (cash inpatient), E2E-06, E2E-13, E2E-14 in `web/tests/e2e/scenarios/`; Phase 1 scenarios still green. |

## Synthetic data you must provide (lane seed steps)

Service catalogue and price lists for the synthetic facility (consultation, lab, imaging,
procedures, bed-days, nursing, drug dispensing; KES `Decimal`; a cash list and a list for at
least one `insurance.Scheme`); a formulary of generic medicines with batches and expiry dates
(FEFO testable, one controlled drug); lab tests with reference ranges and one critical value;
imaging procedures; triage scale configuration; ICD-11 subset with MOH 705 mappings; a
cashier float; open visits in several states, one admitted patient, one emergency; an M-Pesa
fake with scripted outcomes (success, cancelled by user, timeout → query, insufficient funds,
duplicate callback) using Safaricom's published sandbox test values only. Enough history for a
month of MOH reports (E2E-14).

## Done means

CLAUDE.md "Every session ends", `web/CLAUDE.md` "Done means", feature acceptance verified end
to end, `make check` and `make e2e` green on the merged result, delivered to `main`, row
flipped in `features.json` in that delivery, lane progress file updated.
