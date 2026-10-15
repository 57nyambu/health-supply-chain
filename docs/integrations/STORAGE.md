# File Storage — local `data/` by default, S3-compatible bucket by switch

Requirement: files can live in a **Contabo object storage bucket** or **under `data/` at the repo root**, with a way to switch between the two; **local is the default**.

Design in one line: every file goes through `apps/documents/storage.py`; each `Document` row remembers which backend holds its bytes, so both backends can be live at once, a config switch changes where *new* files go, and a migration command moves existing files.

---

## 1. Configuration

| Env var | Default | Meaning |
|---|---|---|
| `STORAGE_BACKEND` | `local` | Backend for new writes: `local` or `s3` |
| `DATA_DIR` | `<repo>/data` (in containers `/app/data`, bind-mounted from `./data`) | Local root |
| `S3_ENDPOINT_URL` | — | e.g. Contabo `https://eu2.contabostorage.com` (EU), `https://usc1.contabostorage.com` (US), `https://sin1.contabostorage.com` (Singapore); any S3-compatible endpoint works |
| `S3_REGION_NAME` | — | value your provider expects (check the provider's S3 docs; Contabo endpoints are region-specific) |
| `S3_BUCKET` | — | private bucket |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | — | least-privilege keys for this bucket only |
| `S3_ADDRESSING_STYLE` | `path` | path-style is the safe default for non-AWS S3 |
| `S3_SIGNATURE_VERSION` | `s3v4` | |
| `STORAGE_ENCRYPTION` | `on` | envelope encryption of every object (§3) |
| `STORAGE_MASTER_KEYS` | — | JSON `{kid: base64(32 bytes)}`, newest first; from the secret store, never the repo |
| `DOCUMENT_MAX_BYTES` | `26214400` (25 MB) | upload limit (claims attachments have their own smaller limit) |
| `DOCUMENT_ALLOWED_TYPES` | `application/pdf,image/jpeg,image/png,image/webp` | allowlist, checked by magic bytes, not just extension |

Implementation: Django 5.2 `STORAGES` with two named backends — `"local"` (`FileSystemStorage(location=DATA_DIR / "objects")`) and `"s3"` (`storages.backends.s3.S3Storage` from django-storages with the options above). `documents.storage.get_backend(name)` returns one; `default_backend()` reads `STORAGE_BACKEND`. Static files and Next.js assets are **not** in this system.

## 2. Residency — read before using Contabo for production

Contabo's object storage regions are the EU, US and Singapore; none is in Kenya. Kenyan law expects health data for primary and secondary care to be stored/processed in Kenya, with transfers out only under prescribed conditions (KE-DHA-06, KE-DPA-07). Therefore:
- **dev / staging with synthetic data:** Contabo is fine.
- **production with real patient files:** use local storage on a Kenya-hosted server, or a Kenyan S3-compatible endpoint — or record an ADR with the legal basis before pointing production at Contabo.
- The residency guard (DESIGN §8.3) enforces this: in `strict` mode the API will not start if `S3_ENDPOINT_URL` is not in `RESIDENCY_ALLOWED_HOSTS`.
- Encryption (§3) reduces breach risk but does not by itself make a cross-border transfer lawful.

## 3. Objects, keys and encryption

- **Object key:** `{env}/{facility_uuid}/{category}/{yyyy}/{mm}/{document_uuid}` — no names, IDs or diagnoses in keys or metadata.
- **Envelope encryption:** a random 256-bit data key per object; content encrypted with AES-256-GCM in 1 MiB chunks (streamable); the data key is wrapped with the current master key; the wrapped key, master `kid` and nonce prefix are stored on the `Document` row. Rotation re-wraps data keys (fast) without rewriting objects.
- **Checksums:** SHA-256 of the plaintext (integrity after decrypt) and of the stored ciphertext (verifies copies between backends).
- **Uploads:** size and type checks (magic bytes), image EXIF stripped, optional ClamAV scan hook (`DOCUMENT_AV_SCAN=on` with a clamd sidecar), encrypt, write to the default backend, then commit the row. Orphaned objects (write succeeded, transaction rolled back) are swept daily.

## 4. `Document` model

`id (UUIDv7)`, `facility`, `patient` (nullable), `visit` (nullable), `category` (`lab_report`, `imaging_report`, `consent_form`, `claim_attachment`, `invoice_pdf`, `receipt_pdf`, `claim_form`, `discharge_summary`, `referral_letter`, `id_scan`, `audit_anchor`, `other`), `sensitivity` (normal / sensitive), `content_type`, `size`, `sha256_plain`, `sha256_cipher`, `storage_backend` (`local`|`s3`), `storage_key`, `enc_kid`, `enc_wrapped_key`, `original_filename_encrypted`, `uploaded_by`, `created_at`, `retention_until`, `legal_hold`, `superseded_by`. No hard delete; deletion happens only through the retention job (DESIGN §8.4).

## 5. Reading files

- Only through `GET /api/v1/documents/{id}/content` (and generated-PDF endpoints that resolve to a document). The view checks the permission and chart access (incl. sensitivity), writes an audit event, then streams the decrypted content (`StreamingHttpResponse`) with `Content-Disposition`, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`.
- No public URLs and no presigned URLs to the browser: objects are ciphertext, so a presigned URL would give the browser nothing it can read, and it would bypass the access check and the audit log. Bucket policy: private, no public ACLs, and the app's key limited to its prefix where the provider supports it.

## 6. Switching and migrating

- Switching: change `STORAGE_BACKEND` and restart. New files go to the new backend; existing files keep reading from the backend recorded on their row. Nothing breaks during a partial migration.
- `python manage.py storage_migrate --from local --to s3 [--category …] [--facility …] [--batch 500] [--dry-run] [--verify] [--purge-source]`
  1. Select rows on the source backend (resumable by cursor).
  2. Copy ciphertext bytes; verify `sha256_cipher` at the destination.
  3. Update `storage_backend` on the row in a transaction.
  4. With `--purge-source` (separate, later run), delete the source object only after the row points at the destination and verification passed.
  5. Report: copied, skipped, failed (with reasons); audit event per batch.
- The same command migrates back (`--from s3 --to local`).
- `storage_verify` checks a sample (or all) objects: exists, ciphertext hash matches, decrypts, plaintext hash matches.

## 7. Backups and operations

- Local: `data/objects/` is part of the nightly backup set (encrypted before leaving the host; destination must respect §2).
- Bucket: enable versioning/lifecycle if the provider supports it; otherwise rely on the nightly sync and `storage_verify`.
- Disk monitoring for `data/` (alert at 75% and 90%).
- `data/` is git-ignored except `data/.gitkeep`; the agent's permissions deny reading `data/**`.

## 8. Tests (both backends, every run)
- The storage test suite is parametrised over `local` (tmp dir) and `s3` (MinIO container in `docker-compose.yml`; `moto` in pure unit tests).
- Scenario E2E-12: upload on local → switch to S3 → upload again → both readable → migrate → all on S3 and verified → switch back.
- Failure cases: S3 unavailable on write (clear error, no orphan row), corrupted object (verification fails, alert), wrong master key (decrypt error surfaces as 500 with alert, no plaintext leak).
