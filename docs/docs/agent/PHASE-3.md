# Phase 3 — Insurance, Banks, Cards, Hardening and Go-Live Readiness

**Goal:** claims flow to SHA through the HIE (and the FHIR bundle path), and to private insurers through SMART and Slade360; payments arrive through Equity, KCB and cards and reconcile daily; eTIMS is ready behind a flag; the system is hardened, deployable, backed up, and the DHA certification evidence pack is complete.

**Session:** a new Claude Code session. Start only if tag `phase-2-complete` exists. Commit to `main`; tag `phase-3-complete` at the end.

## Entry criteria
- `phase-2-complete` tag present; `make check` and `make e2e` green.
- Check PROGRESS.md "Owner actions" for credentials: HIE UAT client ID/secret, SHA tariff spreadsheet, SMART/Slade360 specs, Jenga/Buni/Pesapal sandbox keys, Daraja go-live. Missing credentials do not block the phase: build port → fake → contract tests, and mark the sandbox step as an external dependency.

## Read first
`docs/integrations/INSURANCE.md` (all), `docs/integrations/PAYMENTS.md` §4–9, DESIGN §8, §11, §15, §16, `COMPLETION.md`. Re-read hie-docs.dha.go.ke scenario pages and afyalink.dha.go.ke/claim-integration — they change.

## Work order

| # | Features | Notes |
|---|---|---|
| 1 | P3-INS-01, P3-CLM-01 | Port, models, contract suite, scrubber and queues before any vendor adapter. |
| 2 | P3-SHA-01, P3-SHA-02 | HIE auth/registries/eligibility; consent flows. Wire registry lookups into reception and licence verification. |
| 3 | P3-SHA-03, P3-SHA-04, P3-SHA-05, P3-SHA-06 | Claim lifecycle and scenarios 1–8 in fake mode; then UAT if credentials exist. Exactly-once dispatch with fault injection tests. |
| 4 | P3-SHA-07, P3-SHA-08 | FHIR mapping + AfyaLink path; UAT checklist runner and evidence. |
| 5 | P3-PVT-01, P3-PVT-02, P3-PVT-03 | Fakes and contract tests now; real adapters only from specs. |
| 6 | P3-BNK-01, P3-BNK-02, P3-CRD-01, P3-REC-01 | Signature/IPN verification with test vectors; reconciliation and sign-off. |
| 7 | P3-TAX-01, P3-NOT-01 | eTIMS behind `ETIMS_MODE`; notification hardening. |
| 8 | P3-SEC-01, P3-PERF-01 | ASVS L2 evidence, threat model, breach workflow; load test. |
| 9 | P3-OPS-01, P3-OPS-02 | Production compose, nginx, Jenkins, firewall; backups and a real restore drill. |
| 10 | P3-DOC-01, P3-DOC-02 | Evidence pack, guides, runbooks. |
| 11 | P3-E2E-01 | Full suite, final report, tag. |

## Design reminders
- Local `Claim` is the source of truth; adapters translate.
- Never auto-retry claim submission or payment initiation; on uncertainty, query.
- Consent tokens, OTPs, member numbers: encrypted, redacted, never logged.
- No card data anywhere in our code or logs.
- Residency guard is `strict` in production; production storage and backups stay in Kenya unless an ADR records the legal basis.
- Postgres and Redis are never published on public interfaces; firewall default deny.

## Pitfalls to avoid
- Writing vendor field names from memory or from blog posts. Use official docs, vendor specs or recorded sandbox traffic; log gaps.
- Forgetting the mandatory SHA documents (claim form, itemised invoice, discharge/case summary).
- Treating an unknown per-diem allowance as zero.
- Letting reconciliation silently auto-allocate ambiguous matches — ambiguous goes to suspense.
- Skipping the restore drill: a backup policy without a tested restore fails certification.

## Exit criteria
- Every feature `passes: true` or waived by the owner with a recorded reason (vendor-blocked adapters: fake + contract suite green, real adapter listed as external dependency).
- Full COMPLETION.md scenario suite green; security, performance and restore evidence in `docs/evidence/`.
- `make traceability` shows every `KE-*` requirement covered or marked external/owner.
- `docs/agent/FINAL-REPORT.md` written (COMPLETION.md §10).
- Tag `phase-3-complete` pushed.
