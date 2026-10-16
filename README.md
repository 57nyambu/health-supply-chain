# AfyaSync HMIS

A hospital management information system for Kenyan health facilities — reception to completion of treatment, with SHA integration through the national Health Information Exchange. It grew out of a retail inventory system (AfyaSync); the inventory, stores and procurement parts are kept and extended for health use.

> Work in progress. Phase 1 (foundation and access control) is under way; see `docs/agent/PROGRESS.md` for the current state.

## Repository layout

```
api/      Django 5.2 LTS + DRF modular monolith (manage.py, config/, apps/<domain>/)
web/      Next.js 16 App Router + TypeScript web app (role workspaces)
infra/    docker compose, nginx, Jenkinsfile, systemd units, backup scripts
data/     local object storage root (git-ignored; holds real patient files in production)
docs/     agent/ (design, phases, decisions), compliance/, integrations/, operations/, legacy/
scripts/  developer helper scripts
```

## Getting started

Requirements: Docker with Compose v2, Python 3.12 or 3.13 with [uv](https://docs.astral.sh/uv/), Node.js 22.12+ with pnpm 11, GNU make. Without Docker, run PostgreSQL yourself (`scripts/dev/local-postgres.sh start` gives a private trust-auth cluster on port 5433) and set `DATABASE_URL`.

```bash
make setup   # install api + web dependencies, create .env from .env.example, start services
make dev     # run the dev stack
make seed    # load synthetic data (never real patients)
make check   # the commit gate: lint, types, tests, migrations, OpenAPI drift, contrast, secrets, smoke
make e2e     # the Playwright scenarios (needs SEED_PASSWORD; see docs/operations/ENV.md)
```

Every make target is described in `docs/agent/IMPLEMENTATION.md` §5. Environment variables are documented in `.env.example` and `docs/operations/ENV.md`.

## Documentation

| Document | Purpose |
|---|---|
| `docs/agent/DESIGN.md` | architecture, modules, patient journey, access control, data protection |
| `docs/agent/DESIGN-SYSTEM.md` | the high-contrast light UI design system |
| `docs/agent/IMPLEMENTATION.md` | workflow, toolchain, quality gates, testing |
| `docs/agent/DECISIONS.md` | architecture decision records and research findings |
| `docs/agent/PROGRESS.md` | current status, owner actions, spec gaps |
| `docs/compliance/KENYA-REGULATORY-REGISTER.md` | regulatory requirements (`KE-*`) with sources |
| `docs/integrations/` | SHA and private insurers, payments, storage |
| `docs/operations/` | operating procedures |
| `docs/legacy/` | specifications of the pre-HMIS system, kept for reference |

## Data protection

This system processes health data, which is sensitive personal data under Kenya's Data Protection Act 2019. Never commit `.env` files, databases, dumps, logs or anything under `data/`, and use synthetic data only in development and tests.
