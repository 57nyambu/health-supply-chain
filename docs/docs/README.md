# AfyaSync HMIS — agent design manual (owner's runbook)

This pack instructs a Claude Code agent (Opus 5.5) to rework the repository into a Kenyan hospital management information system in three phases. This page is for you, the owner: how to install the pack, how to run each phase session, and what only you can do.

## What's in the pack
```
CLAUDE.md                     root instructions (loaded every session; ~150 lines)
api/CLAUDE.md                 backend rules (load when the agent works in api/)
web/CLAUDE.md                 frontend rules (load when the agent works in web/)
.claude/settings.json         model (Opus 5.5, xhigh effort) + permissions (no reading .env or data/, no force-push)
docs/agent/DESIGN.md          architecture, patient journey, UAC, data protection, billing, reporting
docs/agent/DESIGN-SYSTEM.md   Flat 2.0 high-contrast light UI (tokens with verified contrast)
docs/agent/IMPLEMENTATION.md  session protocol, git, toolchain, quality gates, testing
docs/agent/PHASE-1|2|3.md     phase briefs
docs/agent/COMPLETION.md      definition of done, 16 acceptance scenarios, evidence pack, go-live
docs/agent/features.json      91-feature ledger (33 / 32 / 26 per phase)
docs/agent/DECISIONS.md       16 ADRs (one awaiting your decision: ADR-006 hosting)
docs/agent/PROGRESS.md        the agent's running log (starts with your action list)
docs/compliance/KENYA-REGULATORY-REGISTER.md   39 requirement IDs with sources
docs/integrations/INSURANCE.md | PAYMENTS.md | STORAGE.md
docs/operations/CASH-HANDLING-SOP.md
```

## Install
1. Unzip at the repository root (it merges `docs/`, `api/`, `web/`, `.claude/` with what is there; `api/` and `web/` only contain `CLAUDE.md` until Phase 1 moves code in).
2. Commit on `main`: `git add CLAUDE.md api/CLAUDE.md web/CLAUDE.md .claude/settings.json docs && git commit -m "docs: add agent design manual"` and push.
3. Make sure the machine running Claude Code has Docker, Python 3.12, `uv`, Node 24 and `pnpm`, and that Claude Code is up to date.
4. Create `.env` yourself from `.env.example` once Phase 1 generates it (the agent is denied read access to `.env` files on purpose). Sandbox keys go there.

## Run the phases
Open a terminal at the repo root and start `claude` (the project settings select Opus 5.5 at `xhigh` effort; `/effort high` is fine for routine stretches). Use one session per phase. If a session ends before its phase is done, start a new one with the same prompt — the agent resumes from `PROGRESS.md`.

**Phase 1 prompt**
> Start Phase 1. Follow CLAUDE.md: read PROGRESS.md and docs/agent/PHASE-1.md, do the legacy inventory first, then work through the Phase 1 features in order until the exit criteria pass and phase-1-complete is tagged. Ask me only for decisions listed as owner decisions.

**Phase 2 prompt** (only after `phase-1-complete` exists)
> Start Phase 2. Follow CLAUDE.md and docs/agent/PHASE-2.md. Continue until the exit criteria pass and phase-2-complete is tagged.

**Phase 3 prompt** (only after `phase-2-complete` exists)
> Start Phase 3. Follow CLAUDE.md and docs/agent/PHASE-3.md. Credentials available: <list what you've added to .env>. Continue until the exit criteria pass and phase-3-complete is tagged.

Tip: for the first hour of each phase, plan mode (Shift+Tab) lets you review the agent's plan before it edits code.

## What only you can do (start now — these have long lead times)
| Action | Why | Blocks |
|---|---|---|
| Decide production hosting for real patient data (ADR-006) | Kenyan law expects health data stored in Kenya; Contabo has no Kenyan region | go-live |
| DHA: register on certification.dha.go.ke; request HIE UAT credentials; book the UAT demo | SHA contracting needs a DHA-certified, HIE-integrated HMIS (deadline extended to end Sept 2026, with an October rapid-results window) | SHA live |
| SHA: current Benefits and Tariffs spreadsheet; facility FID; callback URL setup | claim mapping | P3-SHA-* |
| ODPC registrations (each facility as controller; your company as processor) | Data Protection Act; DHA certification evidence | go-live |
| SMART and Slade360 partner agreements + API specs + test credentials | private insurance claims | P3-PVT-* real adapters |
| Daraja go-live; JengaHQ onboarding; KCB Buni app + go-live letter; Pesapal merchant account | payments live | live payments |
| KRA eTIMS approach | invoicing compliance | P3-TAX-01 live |

## Decisions with defaults (change them by telling the agent, it records an ADR)
- Hosting: Kenya-hosted production; Contabo for dev/staging (ADR-006).
- Insurers: SHA + SMART + Slade360 + manual claim packs; M-TIBA optional.
- Banks/cards: Equity (Jenga), KCB (Buni), Pesapal hosted checkout, bank PDQ terminals.
- Waiver thresholds: KES 5,000 / 50,000; elective deposit 50% of estimate.
- eTIMS: adapter built, switched off until you decide.
