# Progress Log

The agent updates this file at the end of every session (and before context runs low). Newest session on top. Keep it factual and short; details belong in commits.

## Current state
- **Active phase:** 1 (not started)
- **Last tag:** none
- **`main` status:** unknown — run `make check` (or the legacy test command) at session start
- **Next feature:** P1-REPO-01 (after the legacy inventory in PHASE-1.md "Before writing code")

## Owner actions (external, long lead time — start now)
- [ ] Decide production hosting for real patient data (ADR-006): Kenya-hosted, or Contabo with documented legal basis
- [ ] HIE/SHA: request UAT credentials, get the current SHA Benefits and Tariffs spreadsheet, confirm facility FID(s)
- [ ] DHA certification: register on certification.dha.go.ke (business account); plan the UAT demo
- [ ] ODPC: registration for each facility (controller) and for the vendor/host (processor)
- [ ] SMART and Slade360: integration agreements, API specs, test credentials
- [ ] Daraja (shortcode, passkey, initiator), JengaHQ merchant onboarding, KCB Buni app + go-live letter, Pesapal merchant account
- [ ] KRA eTIMS: decide system-to-system (OSCU/VSCU) or KRA tools at go-live
- [ ] Rotate any secrets the P1-REPO-02 scan finds; decide whether to rewrite git history (agent will not do it unasked)

## Questions for owner
<!-- - [Q-001] question — options — recommendation — default used meanwhile -->

## Spec gaps
<!-- - [GAP-XXX-NNN] integration/operation — unknown — assumption in fake — risk — owner action -->

## Legacy inventory
<!-- Filled in during Phase 1 "Before writing code": apps, models, endpoints, tests baseline, frontend tech, ai endpoints, secrets found -->

## Session log

<!--
### Session YYYY-MM-DD — Phase n
Done this session:
- P1-XXX-NN — one line on what changed (commit abc1234)
Verified:
- make check ✔, make e2e ✔ (or what failed and why)
Next:
- P1-XXX-NN — first step
Blockers / risks:
- …
Decisions:
- ADR-0NN …
-->
