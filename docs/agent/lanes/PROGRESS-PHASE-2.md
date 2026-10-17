# Phase 2 lane — progress log

Written only by the Phase 2 lane (docs/agent/lanes/README.md). Newest session on top.
The integration session copies the essentials into docs/agent/PROGRESS.md when it folds
the lane in.

## Current state
- **Branch:** `lane/phase-2` (created from `origin/main` at `b16ec0b`, 2026-10-17)
- **Last delivery to main:** none yet (row 1 being gated)
- **Next:** row 2 — P2-TRI-01, P2-CLI-01, P2-CLI-02, P2-CLI-03 (terminology app started, parked until row 1 is delivered)

## Deliveries to main
<!-- - YYYY-MM-DD `<sha>` — features … (make check, make e2e green on the merged result) -->

## Seams published / consumed
- Emitted (SEAMS §2): `visits.visit.opened` (`visit_id`, `patient_id`, `visit_type`, `coverage_id`) and `visits.visit.closed` (`visit_id`, `outcome`: `closed` / `cancelled` / `left_before_seen`) from `apps.visits.services`.
- `billing.Service` carries `sha_interventions: list[str]` (synthetic `SYN-SHA-…` codes in the seed) and `etims_item_code` (SEAMS §3).
- Gate engine extension points for the Phase 3 lane (ADR-041): `apps.visits.gates.register_flagger(name, fn(visit, context, subject) -> bool)` switches on "pre-authorisation if flagged" and "uncovered pharmacy items"; `register_checker(gate, fn)` may replace the cover-verification check (today `Coverage.verification == "verified"`). Emergency visits and discharge never reach a checker.
- Slot W1 (`PayerEligibility`) is rendered in the visit-opening form on `/patients/<id>` under the payer choice, with `patientId` and `coverageId` (null for cash).
- Consumed: `apps.insurance.selectors.is_current`, `Coverage.verification`, `Scheme`/`Payer` (price lists keyed by scheme or payer).

## Requests to integrator
- [REQ-P2-001] `web/playwright.config.ts` uses fixed ports (API 8000, S3 API 8001, web 3100) with `reuseExistingServer: true` for the API servers. When two lanes run browser scenarios on this machine at the same time, one lane's specs silently run against the other lane's API (different code, different database). Please make the ports configurable (e.g. `E2E_API_PORT`, `E2E_S3_API_PORT`, `E2E_WEB_PORT`) and reuse an API server only with `E2E_REUSE=1`. Meanwhile this lane checks the ports are free before every run.
- [REQ-P2-002] `web/src/app/(workspace)/admin/approvals/page.tsx`: add labels for the new maker-checker actions (`billing.price.set` "Price change", `billing.service.create` "New service", `visits.gate_policy.set` "Payment gate change") and show a PHI-free payload summary (service, price list, new price; gate context, payer, gate) so the approver sees what they approve. Until then the page shows the raw action code and the requester's reason.

## Questions for owner
<!-- - [Q-P2-001] question — options — recommendation — default used meanwhile -->
- None yet. Defaults in use from DESIGN §20: waiver thresholds A = KES 5,000, B = KES 50,000; elective deposit = estimated bill × 50 % (used from row 7).

## Spec gaps
<!-- - [GAP-XXX-NNN] integration — unknown — assumption in fake — risk — owner action -->

## Session log

### Session 2026-10-17 (1)
Setup: worktree `phase-2-lane-setup-019e37` switched to the new branch `lane/phase-2` (from `origin/main`), pushed. Local environment: no Docker; the lane uses its own databases `afyasync_p2` / `test_afyasync_p2` on the private trust-auth cluster `127.0.0.1:5433`, Redis db 2, and a private pytest temp dir (the shared `pytest-of-xc` directory is not readable from this session). Baseline on `main`: 553 API tests green.

Done (not delivered yet):
- `core.money` (2 dp, ROUND_HALF_UP, floats refused, M-Pesa whole-shilling round-up) with hypothesis tests.
- P2-BIL-01 — `apps.billing`: `Service` (kinds, revenue code, SHA interventions, eTIMS item code), cash / payer / scheme `PriceList`s with effective-dated `PriceListItem`s (one open price per list and service; history kept), resolution scheme → payer → cash, price changes and new services through maker-checker (finance manager), seed of 27 services and 3 price lists. Admin tab "Services and prices".
- P2-VIS-01 — `apps.visits`: visit types, numbering, the state machine with append-only transitions (ADR-040), queues per service point per day with triage-then-priority-then-arrival ordering, call next / recall / skip / transfer / send back / prioritise (audited), left-before-seen flag after N calls or idle time (beat job `p2-flag-idle-tickets`) with a confirm/dismiss work queue, care-team membership on call, visit hooks for billing. Remaining for this feature: "unrendered charges reversed" lands with P2-BIL-02 (hook `ended`).
- P2-VIS-02 — gate engine (ADR-041): defaults seeded per facility, maker-checker changes, emergency and discharge never gated (tests for every context and payer), overrides audited and listed on the visit; `gates.enforce` audits every emergency bypass. Remaining: "override shows on the bill" lands with P2-BIL-03.
- P2-VIS-03 — TV boards with board-scoped device tokens (ADR-042), `/board#<token>`, admin tab "Queue boards".
- Web: visit opening on `/patients/<id>` (Alt+N, slot W1), journey rail driven by `Visit.status`, `/queue` workspace with `QueueList` (Alt+C), admin tabs. Playwright `tests/e2e/phase2/visits.spec.ts` (5 tests, axe clean). Screens: [visit opened](../../evidence/screens/p2-vis-01-visit-opened.png), [queue](../../evidence/screens/p2-vis-01-queue.png), [board](../../evidence/screens/p2-vis-03-board.png), [gates](../../evidence/screens/p2-vis-02-gates.png), [services](../../evidence/screens/p2-bil-01-services.png).
- ADR-040, ADR-041, ADR-042.
