# AfyaSync HMIS — developer and CI entry points (contract: docs/agent/IMPLEMENTATION.md §5).
# `make check` is the commit gate. Run `make help` for the list.

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

UV       ?= uv
PNPM     ?= pnpm
COMPOSE_FILE ?= infra/docker-compose.yml
ENV_FILE := $(if $(wildcard .env),--env-file .env,)
COMPOSE  ?= docker compose -f $(COMPOSE_FILE) $(ENV_FILE)
API      := cd api && $(UV) run
REPORTS  := reports
HAS_WEB  := $(wildcard web/package.json)
COVERAGE_MIN ?= 85

.PHONY: help setup dev down seed reset-dev test test-api test-web e2e smoke lint typecheck \
        check check-fast migrations-check openapi openapi-check role-matrix traceability \
        contrast secrets secrets-history deps-audit audit-verify services toolchain seed-e2e

help: ## List targets
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-18s %s\n", $$1, $$2}'

# --- Environment ---------------------------------------------------------------------------------

toolchain: ## Check required tool versions
	@scripts/dev/check-toolchain.sh

setup: toolchain ## Install api + web deps, Playwright, .env from .env.example, start services, migrate
	@test -f .env || { cp .env.example .env && echo "Created .env from .env.example (dev-safe defaults)."; }
	cd api && $(UV) sync --frozen
	@if [ -n "$(HAS_WEB)" ]; then cd web && $(PNPM) install --frozen-lockfile && $(PNPM) exec playwright install chromium; fi
	@$(MAKE) --no-print-directory services
	$(API) python manage.py migrate --noinput

services: ## Start postgres, redis, minio, mailpit (docker compose)
	@if command -v docker >/dev/null 2>&1; then \
		$(COMPOSE) up -d --wait postgres redis minio mailpit; \
	else \
		echo "docker not found: start PostgreSQL and Redis yourself (scripts/dev/local-postgres.sh) and set DATABASE_URL/REDIS_URL."; \
	fi

dev: ## Start the full dev stack (api, worker, beat, web + services)
	$(COMPOSE) up -d --build --wait
	@echo "web http://127.0.0.1:3000  api http://127.0.0.1:8000  mail http://127.0.0.1:8025  minio http://127.0.0.1:9001"

down: ## Stop the dev stack
	$(COMPOSE) down

seed: ## Load synthetic data (refuses in production)
	$(API) python manage.py seed

reset-dev: ## Wipe the dev database and data/ objects (dev only; refuses in production)
	$(API) python manage.py reset_dev --yes

# --- Tests ---------------------------------------------------------------------------------------

test: test-api test-web ## All unit/integration tests

test-api: ## pytest with coverage gates
	@mkdir -p $(REPORTS)
	$(API) pytest --cov --cov-report=term --cov-report=json:../$(REPORTS)/coverage.json \
		--cov-report=xml:../$(REPORTS)/coverage.xml --junitxml=../$(REPORTS)/pytest.xml
	$(API) python ../scripts/ci/coverage_gate.py ../$(REPORTS)/coverage.json --total $(COVERAGE_MIN)

test-web: ## vitest
	@if [ -n "$(HAS_WEB)" ]; then cd web && $(PNPM) test; else echo "test-web: web/ not scaffolded yet (P1-WEB-01)"; fi

e2e: seed-e2e ## Playwright scenario suite (fake integrations, synthetic seed; needs SEED_PASSWORD)
	@if [ -n "$(HAS_WEB)" ]; then cd web && $(PNPM) e2e; else echo "e2e: web/ not scaffolded yet (P1-WEB-01)"; fi

smoke: seed-e2e ## Playwright smoke: login, open a workspace, axe clean (needs SEED_PASSWORD)
	@if [ -n "$(HAS_WEB)" ] && [ -f web/tests/e2e/smoke.spec.ts ]; then cd web && E2E_STORAGE=off $(PNPM) smoke; \
	else echo "smoke: login UI not built yet (P1-WEB-03)"; fi

seed-e2e: ## Idempotent synthetic seed of the DJANGO_ENV=dev database for browser scenarios
	@if [ -z "$$SEED_PASSWORD" ]; then echo "Set SEED_PASSWORD (the synthetic seed password) to run browser scenarios." >&2; exit 1; fi
	cd api && DJANGO_ENV=dev $(UV) run python manage.py seed

# --- Static checks ------------------------------------------------------------------------------

lint: ## ruff (+ eslint)
	$(API) ruff check .
	$(API) ruff format --check .
	@if [ -n "$(HAS_WEB)" ]; then cd web && $(PNPM) lint; fi

typecheck: ## mypy (+ tsc)
	$(API) mypy .
	@if [ -n "$(HAS_WEB)" ]; then cd web && $(PNPM) typecheck; fi

migrations-check: ## Fail on missing migrations
	$(API) python manage.py makemigrations --check --dry-run

openapi: ## Regenerate api/openapi.yaml and the typed web client
	DJANGO_ENV=test $(API) python manage.py spectacular --file openapi.yaml
	@if [ -n "$(HAS_WEB)" ]; then cd web && $(PNPM) openapi; fi

openapi-check: ## Fail when the committed schema or web client is stale
	$(API) pytest -q -p no:cacheprovider tests/test_openapi.py
	@if [ -n "$(HAS_WEB)" ]; then cd web && $(PNPM) openapi:check; fi

role-matrix: ## Regenerate docs/generated/role-matrix.csv
	$(API) python manage.py role_matrix --output ../docs/generated/role-matrix.csv

traceability: ## Regenerate docs/generated/traceability.md from req("KE-…") markers
	$(UV) run --project api python scripts/ci/traceability.py

contrast: ## Design-token contrast check
	@if [ -n "$(HAS_WEB)" ]; then cd web && $(PNPM) contrast; else echo "contrast: design tokens not created yet (P1-WEB-02)"; fi

secrets: ## gitleaks on staged and unstaged changes
	gitleaks git --staged --redact --no-banner --log-level warn .
	gitleaks git --pre-commit --redact --no-banner --log-level warn .

secrets-history: ## gitleaks over the full git history (CI)
	gitleaks git --redact --no-banner .

deps-audit: ## pip-audit + pnpm audit; high/critical findings fail
	@mkdir -p $(REPORTS)
	cd api && $(UV) export --frozen --no-hashes --format requirements-txt > ../$(REPORTS)/requirements-audit.txt
	$(UV) run --project api pip-audit --strict --no-deps --disable-pip -r $(REPORTS)/requirements-audit.txt
	@if [ -n "$(HAS_WEB)" ]; then cd web && $(PNPM) audit --audit-level high --prod; fi

audit-verify: ## Verify the audit hash chain
	$(API) python manage.py audit_verify

# --- Gates ----------------------------------------------------------------------------------------

check-fast: lint typecheck ## Lint, types and unit tests without coverage gates
	$(API) pytest -q -x
	@if [ -n "$(HAS_WEB)" ]; then cd web && $(PNPM) test; fi

check: lint typecheck test-api migrations-check openapi-check test-web contrast secrets smoke ## The commit gate
	@echo "make check: all gates passed"
