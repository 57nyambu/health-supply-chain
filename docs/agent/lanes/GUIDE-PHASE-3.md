# Guide — Phase 3 lane (insurance, banks, cards, eTIMS, hardening)

You build Phase 3 (`docs/agent/PHASE-3.md`, the `P3-*` rows of `features.json`) on the
branch `lane/phase-3`, in parallel with the Phase 2 lane and the integration session
(ADR-024). Read `docs/agent/lanes/README.md` (how lanes work together) and `SEAMS.md`
(contracts) first; they override anything here that conflicts.

## Owner decisions behind this lane

- **Vendor systems are infrastructure now, verification later.** SHA (HIE), SMART, Slade360,
  Equity Jenga, KCB Buni, Pesapal and KRA eTIMS need specifications, agreements and
  credentials the owner is still arranging (PROGRESS.md owner actions). For each: port →
  fake → contract tests → the full domain flow in fake mode → synthetic data rich enough to
  exercise every path → spec gaps logged. The real adapter is a stub that refuses to start
  without its credentials and names the gap. Such a feature is finished when everything but
  the vendor step passes; mark it `blocked` with "external: <owner action>" and request the
  owner's waiver in your progress file (PHASE-3 exit criteria).
- You start before `phase-1-complete` and `phase-2-complete` exist. Work in three stages
  (below); stage B waits for Phase 2 deliveries on `main`; you tag `phase-3-complete` only
  after `phase-2-complete`.
- Never write vendor field names from memory (CLAUDE.md rule 6, PHASE-3 pitfalls). Use
  `docs/integrations/*`, the vendors' published docs (hie-docs.dha.go.ke,
  afyalink.dha.go.ke, developer portals) or recorded sandbox traffic; record each finding
  with its URL in DECISIONS.md (Phase 3 findings).

## First session

```bash
git fetch origin
git worktree add ../afyasync-phase-3 -b lane/phase-3 origin/main   # or reuse your checkout
cd ../afyasync-phase-3 && git push -u origin lane/phase-3
make setup && make seed && make check
```
(If `lane/phase-3` already exists on origin, check it out instead.) Then read `CLAUDE.md`,
`api/CLAUDE.md`, `web/CLAUDE.md`, PHASE-3.md, `docs/integrations/INSURANCE.md` (all),
`PAYMENTS.md` §1 and §4–9, DESIGN §8, §11, §15, §16, COMPLETION.md and
`docs/agent/lanes/PROGRESS-PHASE-3.md`.

## What you own

`apps/insurance` (exists: `Payer`, `Scheme`, `Coverage`, selectors, API, synthetic seed — extend,
never remove or rename those fields), new apps `interop` (FHIR mapping, HIE client), `banking`
(Jenga, Buni, Pesapal, PDQ, reconciliation), `etims`, `privacy` (breach workflow), the real
HIE adapters in `apps/patients/adapters/client_registry/` and
`apps/accounts/adapters/hwr/`; web route `claims`, payer set-up pages,
`components/insurance/` (slot W1) and `components/banking/` (slot W2);
`api/config/lanes/phase3.py`, `web/src/app/(workspace)/admin/sections-phase3.ts`. After
`phase-1-complete`: `infra/`, the Jenkinsfile and the Makefile for P3-OPS-01/02. Never edit
Phase 2's apps or routes, or Phase 1 apps beyond the two adapter folders.

## Stages and work order

**Stage A — now (no Phase 2 dependency).**

| Features | Lane notes |
|---|---|
| P3-INS-01 | `PayerGateway` port and shared error taxonomy (INSURANCE.md §2); the contract suite `apps/insurance/tests/contract/` runs against every fake; extend `Coverage` (eligibility snapshots, consent records) in `apps/insurance`. `apps/insurance/seams.py`: Protocols for SEAMS §3 with fakes. |
| P3-SHA-01, P3-SHA-02 | HIE client (auth, facility scoping, registries, eligibility, tariff import into insurance tables) in fake mode; real Client Registry and HWR adapters next to the existing fakes (fake stays the default; `*_MODE=sandbox|live` refuse without credentials). Eligibility sets `Coverage.verification` and emits `insurance.coverage.verified`. Consent (OTP / biometric) flows. Fill slot W1 `PayerEligibility`. |
| P3-PVT-01, P3-PVT-02, P3-PVT-03 | SMART, Slade360 fakes and contract tests; manual claim pack (PDF through `documents`). |
| P3-BNK-01, P3-BNK-02, P3-CRD-01 (vendor part) | Vendor clients, signature/IPN verification with test vectors, fakes, contract tests in `apps/banking` — without importing `payments`. Register webhook providers `jenga`, `buni`, `pesapal` with `apps.integrations.webhooks`. |
| P3-TAX-01 (vendor part) | eTIMS client and fake behind `ETIMS_MODE` (default off). |

**Stage B — after Phase 2 delivers** P2-VIS-01, P2-BIL-01…03 and P2-PAY-01 to `main` (check
`features.json` on `main`; merge `main` first).

| Features | Lane notes |
|---|---|
| P3-CLM-01 | Claims workbench from SEAMS §3 selectors and §2 events (consume `billing.invoice.finalized`, `billing.charge.*`, `visits.visit.*`). Replace your seam fakes with the real selectors. |
| P3-SHA-03…P3-SHA-08 | Claim session, exactly-once dispatch with fault injection, preauth, ECCIF 24-hour deadline, PHC capitation and SHIF per diem, FHIR mapping and AfyaLink transport, UAT checklist runner — all in fake mode, scenarios 1–8. |
| P3-BNK/CRD glue, P3-REC-01 | Implement the `PaymentProvider` port (SEAMS §5) for your providers; fill slot W2 `ExtraPaymentMethods`; reconciliation engine and finance sign-off (ambiguous matches go to suspense). |
| P3-TAX-01 | Invoice hook (consume `billing.invoice.finalized`) when `ETIMS_MODE` is on. |

**Stage C — after Phase 2 is feature-complete (P2-E2E-01) and `phase-1-complete` exists.**
P3-NOT-01 (after P2-APP-01), P3-SEC-01, P3-PERF-01, P3-OPS-01, P3-OPS-02 (owner's hosting
decision, ADR-006), P3-DOC-01, P3-DOC-02, P3-E2E-01 (E2E-03, 07, 08, 09, 10 and the `[P3]` steps
of 02, 04, 05; E2E-16).

## Synthetic data you must provide (lane seed steps)

Extend the existing insurance seed: per-scheme benefit rules and SHA intervention codes and
tariffs marked synthetic (`SYN-…`, clearly not the real spreadsheet) until the owner provides
it; members and dependants for the seeded cover; a fake HIE with scripted outcomes —
eligible, not eligible, inactive, not found, outage/timeout, consent OTP success / wrong /
expired, biometric success / failure, preauth approved / partially approved / declined /
pending, claim approved / partially approved / rejected with reason codes / queried /
"outcome unknown" (exactly-once tests), remittance advice files; SMART and Slade360 fakes with
member cards, benefits and remittances; bank IPN test vectors (valid, bad signature,
duplicate, amount mismatch, unknown reference), Pesapal checkout and IPN, PDQ capture; an
eTIMS fake returning control numbers and QR data. All synthetic, deterministic and
documented in your progress file, so the owner can demo every path before credentials arrive.

## Done means

CLAUDE.md "Every session ends", `web/CLAUDE.md` "Done means", feature acceptance verified
end to end in fake mode, contract suites green, `make check` and `make e2e` green on the
merged result, delivered to `main`, row updated in `features.json` (`passes: true`, or
`blocked` + waiver request for vendor steps), lane progress file updated.
