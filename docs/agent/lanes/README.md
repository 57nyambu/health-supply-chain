# Parallel build lanes — coordination and reconciliation (ADR-024)

Phase 2 and Phase 3 are built at the same time by two agents, each on its own branch, while
the integration session finishes Phase 1 on `main`. This file is the contract between them.
Read it fully before your first commit; when it and another document disagree on *how lanes
work together*, this file wins. Everything else in `CLAUDE.md` still applies.

## 1. Lanes

| Lane | Branch | Owns | Guide | Tag it creates |
|---|---|---|---|---|
| Integration (Phase 1) | `main` | Phase 1 features, shared files (§3), folding lanes in (§7) | `docs/agent/PHASE-1.md` | `phase-1-complete` |
| Phase 2 | `lane/phase-2` | `docs/agent/PHASE-2.md` — clinical journey, billing core, cash, M-Pesa | `GUIDE-PHASE-2.md` | `phase-2-complete` |
| Phase 3 | `lane/phase-3` | `docs/agent/PHASE-3.md` — insurance, banks, cards, eTIMS, hardening; vendor parts as infrastructure | `GUIDE-PHASE-3.md` | `phase-3-complete` |

Each lane works in **its own git worktree or clone** (never in another lane's checkout) and
pushes only its own branch — except the fast-forward delivery to `main` in §5.

## 2. What each lane may touch

**Rule of thumb: create new files in apps and folders you own; edit shared files only in the
lane blocks made for you; never edit the other lane's files.** If you need something outside
your area, write it under "Requests to integrator" in your lane progress file and carry on
with other work.

### API (`api/apps/`)

| Area | Owner | Notes |
|---|---|---|
| `visits`, `clinical`, `terminology`, `orders`, `laboratory`, `imaging`, `pharmacy`, `inpatient`, `referrals`, `billing`, `payments` (core, cash, M-Pesa, provider port), `reporting` (new) | Phase 2 | Create them as you reach their features (DESIGN §4 names). |
| Legacy `products`, `warehouses`, `suppliers`, `procurement`, `sales`, `analytics`, `facility_ops` | Phase 2 | Inventory upgrade (P2-INV-01) and reporting; keep their tests green. |
| `insurance` (exists: `Payer`, `Scheme`, `Coverage`) | Phase 3 | Phase 2 only **reads** it through `apps.insurance.selectors` and the `/api/v1/insurance/` API. |
| `interop` (FHIR mapping, HIE client), `banking` (Jenga, Buni, Pesapal, IPN inbox, reconciliation), `etims`, `privacy` (breach workflow) (new) | Phase 3 | `banking` plugs into `payments` only through the provider port Phase 2 publishes (SEAMS.md §3). |
| `apps/patients/adapters/client_registry/`, `apps/accounts/adapters/hwr/` | Phase 3 | Real HIE adapters next to the existing fakes. Nothing else in those apps. |
| Phase 1 apps: `core`, `accounts`, `access`, `audit`, `facilities`, `patients`, `documents`, `integrations` | Integration | **Phase 2 may make additive changes** (new fields, models, migrations, selectors — e.g. `patients.selectors.chart_sections`, new document categories, new service-point kinds). **Phase 3 may not** (except the two adapter folders above, and `integrations` notification channels for P3-NOT-01 once Phase 2's P2-APP-01 is on `main`). |
| `apps/access/reserved.py` | each lane, own blocks | Move a domain's codes into `apps/<app>/permissions.py` in the same commit that creates the app; delete only your domains' blocks (Phase 2: visits, clinical, orders, laboratory, imaging, pharmacy, inpatient, referrals, billing, payments, reporting; Phase 3: privacy, tax/eTIMS codes it adds). |
| `apps/access/roles.py` | Integration | Lanes add grants in `config/lanes/phase<N>.py` → `ROLE_GRANTS`. All roles both phases need already exist. |
| `config/settings/*`, `config/urls.py`, the seed command | Integration | Lanes register apps, URLs, seed steps, beat jobs and settings in `config/lanes/phase<N>.py`. |

### Web (`web/`)

| Area | Owner | Notes |
|---|---|---|
| Routes `triage`, `consult`, `lab`, `imaging`, `pharmacy`, `wards`, `cashier`, `billing`, `queue`, `reports`, `inventory`, `patients/[id]` (clinical sections, journey from visits), `reception` (visit opening) | Phase 2 | |
| Routes `claims`, payer setup pages, `components/insurance/`, `components/banking/` | Phase 3 | The two extension slots (SEAMS.md §W) are Phase 3 files that Phase 2 renders. |
| `components/ui/`, `components/shell/`, `components/clinical/`, `lib/` | Integration; **Phase 2 may add files and make backward-compatible changes**; Phase 3 adds new files only (under its own folders) | |
| `app/(workspace)/admin/sections-phase<N>.ts` | your lane | Admin tabs. Never edit `sections.ts`. |
| `lib/auth/workspaces.ts` | Phase 2 | Phase 3's `/claims` page exists as a route; it needs no edit there. |
| `web/tests/e2e/support.ts`, `web/playwright.config.ts` | Integration | Lane helpers go in `web/tests/e2e/lanes/phase<N>.ts`; lane specs in `web/tests/e2e/scenarios/` (one per scenario ID) or `web/tests/e2e/phase<N>/`. |

### Repository files

| File | Rule |
|---|---|
| `docs/agent/features.json` | Edit only your phase's rows (`status`, `passes`). Never acceptance criteria. |
| `docs/agent/PROGRESS.md` | Integration only. Lanes log in `docs/agent/lanes/PROGRESS-PHASE-<N>.md`. |
| `docs/agent/DECISIONS.md` | ADR numbers — integration ADR-024…039, Phase 2 ADR-040…069, Phase 3 ADR-070…099 — written inside your lane's section; findings in your lane's findings subsection. |
| `.env.example`, `docs/operations/ENV.md` | Append only inside your lane's section ("Phase 2 lane", "Phase 3 lane"). |
| `api/openapi.yaml`, `web/src/lib/api/schema.d.ts`, `docs/generated/*` | Generated. Never hand-merge: after merging, run `make openapi`, `make role-matrix`, `make traceability` and commit the output. |
| `api/pyproject.toml` + `api/uv.lock`, `web/package.json` + `web/pnpm-lock.yaml` | Add dependencies with `uv add` / `pnpm add --save-exact` (ADR-022, never `minimumReleaseAgeExclude`). On a lockfile conflict take `main`'s side, re-run your `uv add` / `pnpm add`, commit. |
| `Makefile`, `infra/`, `infra/jenkins/Jenkinsfile` | Integration until `phase-1-complete`; then Phase 3 (P3-OPS-01/02). Phase 2 never. |
| `docs/integrations/INSURANCE.md`, `PAYMENTS.md` §4–9 | Phase 3. `PAYMENTS.md` §1–3, `docs/operations/CASH-HANDLING-SOP.md`: Phase 2. |
| `docs/compliance/KENYA-REGULATORY-REGISTER.md`, `CLAUDE.md`, `docs/agent/DESIGN*.md`, `PHASE-*.md`, `COMPLETION.md`, this folder's README/SEAMS | Integration. Lanes request changes. |

### Migrations

Only in apps you own (Phase 2 also in Phase 1 apps, additively). After every merge of `main`
run `cd api && uv run python manage.py makemigrations --check --dry-run`. If an app has two
leaf migrations, create a merge migration (`makemigrations --merge <app>`); never edit,
renumber or squash an applied migration (CLAUDE.md rule 11).

## 3. Shared seams already on `main`

Built before the lanes started so neither invents its own (details in `SEAMS.md`):

- `config/lanes/phase2.py`, `phase3.py` — each lane's apps, URLs, seed steps, beat jobs, settings and role grants.
- `apps.core.events` — transactional outbox: `emit()` in your service transaction, `@consumer(topic, name=…)` in your app; `relay` runs every minute; consumers are idempotent.
- `apps.insurance` — `Payer`, `Scheme`, `Coverage` (+ synthetic SHA, insurer and employer schemes; cover for about a third of the seed patients) with `selectors` and `/api/v1/insurance/schemes/`, `/coverages/`.
- Web slots `components/insurance/payer-eligibility.tsx`, `components/banking/payment-methods.tsx` (render nothing until Phase 3 fills them).
- `admin/sections-phase2.ts`, `sections-phase3.ts`.

## 4. Daily sync (both lanes, at least once per working session)

```bash
git fetch origin
git merge --no-ff origin/main          # never rebase, never force-push
# resolve per §2 and §6, then regenerate:
make openapi && make role-matrix && make traceability
make check                             # + make e2e when UI or flows changed
git push origin lane/phase-<N>
```

## 5. Delivering to `main`

Deliver each coherent, green slice (one row of your phase's work order, or a feature) as soon
as it passes — small deliveries keep the other lane close to you.

1. Do the daily sync (§4) so your branch contains the current `main`.
2. Gate the merged result: `make check`, `make e2e`, `make audit-verify` — all green.
3. Fast-forward `main` to your branch: `git push origin lane/phase-<N>:main`.
   If it is rejected (main moved), go back to 1. **Never `--force`.**
4. Note it in your lane progress file: "Delivered `<sha>` — features …".

Because every delivery is a fast-forward of a fully gated branch that already contains
`main`, `main` is always equal to a gated lane head, and simultaneous deliveries serialise
themselves. Update `features.json` (`passes: true`) for a feature only in the delivery that
puts it on `main` with its acceptance verified.

## 6. Conflict playbook

| Conflict | Resolution |
|---|---|
| Generated file (`openapi.yaml`, `schema.d.ts`, `docs/generated/*`) | Take either side, then regenerate (§4) and commit. |
| Lockfile | Take `main`'s, re-add your dependency, commit. |
| `features.json` | Keep both sides' rows — each lane only touched its own. |
| Two leaf migrations in one app | `makemigrations --merge <app>`. |
| `reserved.py` block deleted by one side, edited by the other | The side that created the app wins (its codes now live in `apps/<app>/permissions.py`). |
| Anything in a file the other lane owns | You should not have edited it: drop your change, file a request. |
| Anything in an integration-owned file | Take `main`'s side; file a request for what you needed. |
| A test of the other lane fails after your merge | Do not change their test. Fix your code, or file it in both progress files and ask the integrator. |

## 7. Folding lanes in and tags (integration)

- `phase-1-complete`: integration session, after the owner's Q-001 (PROGRESS.md).
- **Phase 2 done** when every Phase 2 feature passes on `main`, the Phase 2 scenarios and all Phase 1 scenarios are green on `main`, and `phase-1-complete` exists. The Phase 2 lane tags `phase-2-complete` on `main`, then stops editing. The integrator folds `config/lanes/phase2.py` into the shared files (settings, urls, seed, beat, `roles.py`), empties it, and records the fold in PROGRESS.md.
- **Phase 3 done** likewise, after `phase-2-complete` (P3-E2E-01 needs the full suite). Vendor-blocked adapters count as done with the fake and contract suite green and the owner's recorded waiver (PHASE-3 exit criteria).

## 8. Test and synthetic data

Synthetic only (CLAUDE.md rule 2); seeds idempotent; registered as lane seed steps; one
`make seed` builds everything. Each lane guide lists the data it must provide. Integration
fakes default to `*_MODE=fake`; `sandbox`/`live` modes refuse to start without credentials
and name the spec gap.

## 9. Session protocol for lane agents

Start: read `CLAUDE.md`, this file, `SEAMS.md`, your guide, your lane progress file, your
phase brief; `git status`, `git log --oneline -20`; daily sync (§4).
End: commit, push your branch, deliver what is green (§5), update your lane progress file
(done, next, blockers, spec gaps, questions for the owner, requests to integrator).
