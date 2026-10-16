# Environment variables

All configuration that differs per deployment, and every secret, comes from environment variables. `make setup` copies `.env.example` to `.env` for development. In production, set them through the host's secret store or a root-only `.env`; never commit real values. `api/tests/test_env_documented.py` fails when a variable read by the settings is missing from this page or from `.env.example`.

Legend: **Req (prod)** — the API refuses to start in production without a safe value.

## Django

| Variable | Default | Req (prod) | Purpose |
|---|---|---|---|
| `DJANGO_ENV` | `dev` (`prod` for wsgi/asgi) | yes | Selects `api/config/settings/<env>.py`: `dev`, `test` or `prod`. |
| `DJANGO_SECRET_KEY` | dev placeholder | yes | Session/CSRF signing. Production: random, ≥ 50 characters. |
| `DJANGO_DEBUG` | `True` in dev, `False` elsewhere | must be off | Django debug mode. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | yes, no `*` | Host names the API answers to. |
| `CSRF_TRUSTED_ORIGINS` | empty (dev: `http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:3100`) | — | Origins (scheme + host) allowed to send unsafe requests with the CSRF token. In development the Next.js dev server proxies `/api/*` with Django's Host, so its origin must be listed; production is same-host behind nginx. |
| `LOG_LEVEL` | `INFO` | — | Root log level. Logs are JSON on stdout with `request_id`, PHI-scrubbed. |
| `ERROR_TRACKER_DSN` | empty | — | Sentry-compatible DSN. Enabled only when set and its host passes the residency guard (strict mode refuses to start otherwise). Request bodies, cookies, headers and local variables are never sent. |

## Database and broker

| Variable | Default | Req (prod) | Purpose |
|---|---|---|---|
| `DATABASE_URL` | `postgres://afyasync:afyasync@127.0.0.1:5432/afyasync` | yes (PostgreSQL) | Database connection. SQLite is refused. |
| `DB_CONN_MAX_AGE` | `60` | — | Persistent connection lifetime in seconds. |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | — | Celery broker and result backend. |

## Data protection

| Variable | Default | Req (prod) | Purpose |
|---|---|---|---|
| `DATA_DIR` | `<repo>/data` | — | Root of the local object store (DESIGN §13). Holds real patient files in production; back it up. |
| `FIELD_ENCRYPTION_KEYS` | empty | yes | JSON `{"<kid>": "<base64 32-byte key>"}`, newest first. AES-256-GCM field encryption (DESIGN §8.2). |
| `FIELD_BLIND_INDEX_KEY` | empty | yes | Separate HMAC-SHA256 key for blind indexes used in exact-match search. |
| `STORAGE_MASTER_KEYS` | empty | yes | JSON `{"<kid>": "<base64 32-byte key>"}` that wrap per-document data keys (envelope encryption). |
| `STORAGE_BACKEND` | `local` | `local`/`s3` | Backend for new documents. Existing documents keep reading from the backend on their row (docs/integrations/STORAGE.md §6). |
| `S3_ENDPOINT_URL` | empty | with `s3` | S3-compatible endpoint. Must be in `RESIDENCY_ALLOWED_HOSTS` (strict mode refuses to start otherwise). |
| `S3_REGION_NAME` | empty | — | Region name the provider expects. |
| `S3_BUCKET` | empty | with `s3` | Private bucket; no public ACLs. |
| `S3_ACCESS_KEY_ID` | empty | with `s3` | Least-privilege key for this bucket only. |
| `S3_SECRET_ACCESS_KEY` | empty | with `s3` | Secret for the key above (secret store, never the repo). |
| `S3_ADDRESSING_STYLE` | `path` | — | Path-style addressing (safe for non-AWS S3). |
| `S3_SIGNATURE_VERSION` | `s3v4` | — | Request signing version. |
| `STORAGE_ENCRYPTION` | `on` | `on` | Envelope encryption of every object; production refuses `off`. |
| `DOCUMENT_MAX_BYTES` | `26214400` | — | Upload size limit (25 MB). |
| `DOCUMENT_ALLOWED_TYPES` | `application/pdf,image/jpeg,image/png,image/webp` | — | Allowed types, checked by magic bytes. |
| `DATA_RESIDENCY_MODE` | `warn` (`strict` in prod) | `strict`/`warn` | Residency guard (DESIGN §8.3). `off` is refused in production. |
| `RESIDENCY_ALLOWED_HOSTS` | empty | — | Hosts allowed to receive PHI (S3 endpoint, backup target, error tracker, log shipper). Adding a non-Kenyan host needs an ADR. |
| `SEED_PASSWORD` | empty | — | Password for the synthetic users created by `make seed` (dev/CI only; seeding refuses to run without it and in production). |
| `MFA_DEV_BYPASS` | `False` | `False` | Development only (`DJANGO_ENV=dev`): users without an enrolled authenticator are not asked for MFA, so seeded administrators can sign in. Anyone who enrols is still challenged. Production refuses to start with it on. |
| `TRUST_PROXY_HEADERS` | `False` (`True` in prod) | — | Use `X-Real-IP` from nginx as the client IP in audit events. Enable only behind the project's nginx. |
| `DB_APP_ROLE` | empty | recommended | The PostgreSQL role the API connects as in production. Run migrations as the table owner; the audit migration revokes UPDATE, DELETE and TRUNCATE on audit tables from this role. |
| `AI_FEATURES_ENABLED` | `False` | — | Legacy AI endpoints; off until a DPIA covers them (ADR-014). |

## Production transport security

| Variable | Default | Purpose |
|---|---|---|
| `SECURE_SSL_REDIRECT` | `True` | Redirect plain HTTP to HTTPS (nginx terminates TLS and sets `X-Forwarded-Proto`). |
| `SECURE_HSTS_SECONDS` | `31536000` | HSTS max-age. |

## Email and notifications

| Variable | Default | Purpose |
|---|---|---|
| `NOTIFICATION_CHANNEL` | `email` | `email` or `sms` for legacy staff notifications. |
| `EMAIL_BACKEND` | SMTP (console in dev) | Django email backend. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS` | `localhost`, `587`, `True` | SMTP server (Mailpit on 1025 in dev). |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | empty | SMTP credentials (secret). |
| `DEFAULT_FROM_EMAIL` | `alerts@afyasync.local` | Sender address. |
| `SITE_NAME` | `AfyaSync` | Product name used in messages. |

## Authentication

| Variable | Default | Purpose |
|---|---|---|
| `BREACHED_PASSWORDS_FILE` | empty | Extra offline breached-password list (one per line, optionally gzipped) checked in addition to the bundled list. |
| `FACILITY_NETWORK_ALLOWLIST` | `127.0.0.0/8,::1/128` | CIDRs of the facility networks. Sign-ins from any other address need MFA, for every user. Set the facility LAN ranges in production (with `TRUST_PROXY_HEADERS` behind nginx). |
| `PATIENT_SEARCH_RATE` | `60/min` | Patient searches per signed-in user. Every search is audited with the search term stored only as an HMAC. |
| `PIN_RATE` | `10/min` | Workstation PIN attempts (unlock, switch user) per client IP; 5 wrong PINs for a user force a full sign-in. |
| `HWR_MODE` | `fake` | Health Worker Registry adapter for licence verification. Only `fake` exists until P3-SHA-01; other values refuse to verify. |
| `CLIENT_REGISTRY_MODE` | `fake` | HIE Client Registry adapter for reception lookups and imports. Only `fake` exists until the HIE adapter (GAP-CR-001); other values refuse to start a lookup. |
| `LOGIN_RATE` | `20/min` | Login attempts per client IP (DRF throttle); account lockout is separate (5 → delay, 10 → lock). |

## Web (Next.js, `web/`)

| Variable | Default | Purpose |
|---|---|---|
| `API_ORIGIN` | `http://127.0.0.1:8000` | Where `next dev` forwards `/api/*` (compose sets `http://api:8000`). Production does not use it: nginx routes `/api/` to Django. |
| `DESIGN_CATALOGUE` | off | `on` shows the `/design` component catalogue in a production build (it is always on in development). It contains only synthetic examples. |

## Legacy integrations (replaced by adapters in later phases)

| Variable | Purpose |
|---|---|
| `GEMMA_API_KEY`, `GEMMA_MODEL_ASSISTANT`, `GEMMA_MODEL_VISION`, `GEMMA_CACHE_TTL_SECONDS` | Legacy AI endpoints (disabled by `AI_FEATURES_ENABLED`). Secret: `GEMMA_API_KEY`. |
| `PUBLIC_API_RATE` | Throttle for each API client on `/api/v1/public/` (default `120/min`). Clients are created with `manage.py create_api_client`; keys are stored only as HMACs. The legacy shared `PUBLIC_API_KEY` was removed in P1-UAC-03. |
| `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_BUSINESS_SHORTCODE`, `MPESA_PASSKEY`, `MPESA_CALLBACK_URL` | Legacy M-Pesa STK push (secrets). Replaced by `payments/adapters/mpesa` in Phase 2. |
| `AT_USERNAME`, `AT_API_KEY` | Africa's Talking SMS (secret: `AT_API_KEY`). |
