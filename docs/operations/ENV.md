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
| `CSRF_TRUSTED_ORIGINS` | empty | — | Origins (scheme + host) allowed to send unsafe requests with the CSRF token. |
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
| `DATA_RESIDENCY_MODE` | `warn` (`strict` in prod) | `strict`/`warn` | Residency guard (DESIGN §8.3). `off` is refused in production. |
| `RESIDENCY_ALLOWED_HOSTS` | empty | — | Hosts allowed to receive PHI (S3 endpoint, backup target, error tracker, log shipper). Adding a non-Kenyan host needs an ADR. |
| `SEED_PASSWORD` | empty | — | Password for the synthetic users created by `make seed` (dev/CI only; seeding refuses to run without it and in production). |
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
| `PIN_RATE` | `10/min` | Workstation PIN attempts (unlock, switch user) per client IP; 5 wrong PINs for a user force a full sign-in. |
| `LOGIN_RATE` | `20/min` | Login attempts per client IP (DRF throttle); account lockout is separate (5 → delay, 10 → lock). |

## Legacy integrations (replaced by adapters in later phases)

| Variable | Purpose |
|---|---|
| `GEMMA_API_KEY`, `GEMMA_MODEL_ASSISTANT`, `GEMMA_MODEL_VISION`, `GEMMA_CACHE_TTL_SECONDS` | Legacy AI endpoints (disabled by `AI_FEATURES_ENABLED`). Secret: `GEMMA_API_KEY`. |
| `PUBLIC_API_RATE` | Throttle for each API client on `/api/v1/public/` (default `120/min`). Clients are created with `manage.py create_api_client`; keys are stored only as HMACs. The legacy shared `PUBLIC_API_KEY` was removed in P1-UAC-03. |
| `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_BUSINESS_SHORTCODE`, `MPESA_PASSKEY`, `MPESA_CALLBACK_URL` | Legacy M-Pesa STK push (secrets). Replaced by `payments/adapters/mpesa` in Phase 2. |
| `AT_USERNAME`, `AT_API_KEY` | Africa's Talking SMS (secret: `AT_API_KEY`). |
