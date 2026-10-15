# api/ — backend rules

Loaded when you work under `api/`. The root `CLAUDE.md` still applies.

## Stack
- Python 3.12, Django 5.2 LTS, Django REST Framework, drf-spectacular, django-environ, psycopg 3, Celery + Redis, django-storages (S3), argon2-cffi, TOTP (django-otp or pyotp), `cryptography` (AES-GCM, HMAC), httpx for outbound HTTP, `fhir.resources` (R4) for FHIR models.
- `uv` manages dependencies (`pyproject.toml` + `uv.lock`); run everything with `uv run`.
- Tests: pytest, pytest-django, factory_boy, time-machine, respx (httpx mocks), hypothesis, moto/MinIO for S3.
- Quality: ruff (lint + format), mypy with django-stubs and djangorestframework-stubs (strict for new apps).

## App layout
```
apps/<domain>/
  models.py          data + invariants (clean); no cross-app writes
  services.py        all state changes; wrap in transaction.atomic; emit outbox events
  selectors.py       read queries, already scoped by access policy
  policies.py        authorization predicates for this domain
  permissions.py     PermissionDef catalogue for this domain
  api/               serializers.py, views.py, urls.py — thin: validate → service → serialize
  adapters/<vendor>/ client.py, mapping.py, fake.py (+ Port protocol in adapters/__init__.py)
  tasks.py           small idempotent Celery tasks that call services
  tests/             unit, api, policy, contract; fixtures/ (sanitised only)
```

## Rules
- Another app's data changes only through that app's `services.py`; reads across apps through `selectors.py`.
- Signals only for cross-cutting concerns (audit hooks), never for business flow.
- New PHI tables use UUIDv7 primary keys and inherit `core.models.PhiModel` (facility FK, created/updated by, `version` for optimistic concurrency). Legacy integer keys stay; never expose sequential IDs of patients or visits in URLs.
- Concurrency: `select_for_update()` for stock decrements, bed assignment, numbering, payment allocation, shift close, intent state changes. Clinical edits use `version` → 409 on conflict.
- Numbers (MRN, invoice, receipt, credit note) come from `core.sequences` — gap-free, row-locked, per facility per year.
- Money: `core.money` helpers; `DecimalField(max_digits=14, decimal_places=2)`; `ROUND_HALF_UP`; serializers output strings.
- Time: store UTC; `TIME_ZONE = "Africa/Nairobi"`; dates of birth are dates with an `estimated` flag.
- Phones normalised to E.164 (`+254…`) with the `phonenumbers` library.
- Errors: RFC 9457 problem+json from the global handler with a stable `code` and `request_id`; never echo PHI.
- Pagination: cursor for patients, visits, audit, transactions; page-number for catalogues.
- Patient search needs ≥ 3 characters or an exact identifier; rate-limited; audited with the query stored as HMAC.
- `Idempotency-Key` required on payment initiation, refunds, claim submission and any POST that calls an external system.

## Authorization
- `DEFAULT_PERMISSION_CLASSES` is the policy class: default deny. Each view sets `policy = "<domain>.<resource>.<action>"` or an object-level callable.
- Chart access goes through `access.check_chart_access(user, patient, purpose)` → none / demographics / summary / full / sensitive (DESIGN §7.7); selectors return data shaped to that level.
- `tests/test_policy_matrix.py` asserts `docs/generated/role-matrix.csv`; `test_every_view_has_policy` walks the URLconf.

## Audit
- Writes: `audit.record(action, actor, resource, patient=None, purpose=None, detail={})` inside the service transaction.
- Reads of PHI: middleware for chart opens + explicit calls in selectors returning PHI.
- `detail` holds IDs and codes only — never names, identifiers, phone numbers or clinical text.

## External adapters
- Build order: Port (Protocol) → Fake → contract tests → real adapter → sanitised recorded fixtures.
- Shared httpx client: connect timeout 5 s, read 30 s; retries with jitter only for idempotent reads and 429/5xx; writes never auto-retried.
- Every exchange logged to `integrations.ExchangeLog` (encrypted body, redacted headers, correlation ID, duration, outcome, provider trace ID).
- Callbacks/IPNs: verify (signature, basic auth or secret path + IP allowlist) → store raw encrypted in `WebhookInbox` → 2xx fast → process in Celery, deduped on provider reference.
- Mode per integration from env (`*_MODE=fake|sandbox|live`); `fake` is the default in dev and CI.

## Settings and environment
- `config/settings/{base,dev,test,prod}.py`, chosen by `DJANGO_ENV`. Production refuses to start on unsafe config (P1-API-02).
- Every new env var goes in `.env.example` with a comment and in `docs/operations/ENV.md`.

## Migrations
- `make migrations-check` must pass. Data migrations are idempotent and chunked; reversible, or explicitly irreversible with the reason in the migration docstring.
- Never rename apps that have migrations (`accounts` owns `AUTH_USER_MODEL`). Never edit applied migrations.
