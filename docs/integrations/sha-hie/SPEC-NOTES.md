# SHA / HIE — what the adapter uses from the published specs

Source: the OpenAPI 3.1 specs published with the HIE documentation (https://hie-docs.dha.go.ke/catalog —
"Authentication and Authorization", "HIE Registries", "eClaims and Preauth APIs", "Consent Services APIs"),
read on 2026-10-17. UAT base `https://ilm-dev.dha.go.ke/uat-middleware/api/v1`. Every call is Bearer-authenticated
(`BearerAuth`, JWT) except the token call. Re-read the specs before UAT: the docs changelog moves.

This file lists only what our code relies on. Field names are the specs'; the meaning of values the specs leave
open is a spec gap (bottom). Adapter code: `api/apps/interop/hie/` (transport, mapping, fake),
`api/apps/insurance/adapters/sha_hie/`, `api/apps/patients/adapters/client_registry/hie.py`,
`api/apps/accounts/adapters/hwr/hie.py`, `api/apps/interop/registries.py`.

## Built (stage A)

| Operation | Request | Response fields we read | Schema |
|---|---|---|---|
| `POST /tenants/token` | form `client_id`, `client_secret` | `access_token`, `expires_in`, `token_type` | `LoginResponse` |
| `GET /patients` | `identification_number`, `identification_type` | `id` (CR ID), `first_name`, `middle_name`, `last_name`, `gender`, `date_of_birth`, `phone`, `identification_type`, `identification_number`, `other_identifications[]` | `Member` |
| `GET /professionals` | `identification_number`, `identification_type=registration_number`, `regulator` | `message.identifiers.client_registry_id`, `message.licenses[].license_end`, `message.membership.registration_id`, `message.membership.is_active` | `PractitionerRegistryResponseEnvelope` |
| `GET /facilities/search` | `identifier`, `identifier-type` | `fidCode`, `frCode`, `officialName`, `kephLevel`, `facilityLicenseStatus`, `facilityLicenseEndDate`, `shaContractStatus`, `shaContractedServices[]`, `SHAOperationStatus.operationalStatus` | `FacilitySummary` |
| `GET /patients/eligibility` | `identification_number`, `identification_type` (default `ClientRegistry ID`) | `memberCrNumber`, `statusCode`, `statusDesc`, `facilityBiometricsEnforced`, `whitelistedForOTP`, `isAlive`, `schemes[].schemeName`, `schemes[].coverage.{status,startDate,endDate,reason,possibleSolution}` | `CoverageResult` |
| `GET /patients/benefits/interventions` | `patient_id`, `page` | paged `results[]`: `code`, `name`, `fund`, `benefitCode`, `accessPoint`, `paymentMechanism`, `needsPreauth`, `needsManualPreauthApproval`, `needsDoctorAuthorization`, `kephLevelTarriff`, `overallTariff`, `applicableDocumentTypes[]`; `totalPages` | `InterventionResponse` / `Intervention` |
| `GET /patients/contacts` | `patient_id` | `results[].{id, contactValue (masked), isConfirmed, active}` | `PatientContactsResponse` |
| `POST /claims/otp` | `patient_id`, `intervention_codes[]`, `contact_id` | `data.consent_request_id` (named in the Send OTP process page) | `SendOTPRequestInput` → `SuccessResponse` |
| `POST /claims/authorize` (biometrics) | `agent_id`, `authorizing_device_os`, `ekyc_provider_id`, `factors[]`, `interventions[]`, `is_biometrics_discharge_authorization`, `is_emergency`, `is_integration`, `patient_id`, `provider`, `service_type`, `work_station_id` | `guid`, `status`, `token`, `authorizationReason`, `shaVerificationRequest.requestUrl` | `BiometricsAuthorizationRequest` → `Authorization` |
| `GET /claims/authorizations` | `guid` or `patient_id` (or `token`) | list of `Authorization` (`guid`, `status`, `token`, `authorizationReason`) | |
| `POST /claims/authorizations/{consent_token}/reject` | — | `message` | `AuthorizationRejectResponse` |
| `POST /claims/visit` | `intervention_codes[]`, `patient_id`, `service_type` (`CAPITATION`/`OUTPATIENT`/`INPATIENT`/`EMERGENCY`), `otp` or `auth_guid`, optional `practitioner_identification_type`/`_number`/`practitioner_regulation_body` | `authorization_code` (the consent token), `visit_number`, `claim_id`, `workflow_state` | `OTPVisitRequest`/`BiometricsVisitRequest` → `ClaimAuthorization` |

Errors: `{error, message}` (`internal_dto.ErrorResponse`) or `{code, details[], error, message, source}`
(`internal_shared.ErrorResponse`). Statuses seen in the specs: 400, 401, 403, 404 (registries), 500.

## Next (stage B — P3-SHA-03…07)

Operations listed in the eClaims spec, to read in full before building: `/claims/interventions` (+ `/restore`,
`/retire`, `/switch`), `/claims/diagnoses`, `/claims/lines` (+ `/edit`, `/resubmit`), `/claims/attachments`,
`/claims/preview`, `/claims/preview/payer`, `/claims/submit`, `/claims/otp/discharge` (`OTPDischarge`:
`consent_token`, `patient_id`), `/claims/discharge`, `/claims/close`, `/claims/emergency` (+ `/protocols`),
`/claims/doctors`, `/claims/doctor-consent`, `/preauths` (+ `/cancel`, `/diagnoses/{icd_code}`, `/doctors`),
`/authorizations/covers`, `/benefits/pmf-tariffs/resolve`, `/benefits/pomsf-rates`, status callbacks
(`/tenants/{tenant_id}/endpoints…`).

## Spec gaps (also in docs/agent/lanes/PROGRESS-PHASE-3.md)

- GAP-HIE-001 — UAT client ID/secret and the facility FR code (owner action).
- GAP-HIE-002 — `GET /patients` "not found": 404 or an empty `Member`? We accept both.
- GAP-HIE-003 — `Member.id` taken as the CR ID; date format of `date_of_birth`/`gender` values not stated.
- GAP-HIE-004 — no identification type for Maisha Namba.
- GAP-HIE-005 — no PUID field in the practitioner response; `identifiers.client_registry_id` used.
- GAP-HIE-006 — `coverage.status`/`statusCode` vocabularies not enumerated; only `ACTIVE` counts as active.
- GAP-HIE-007 — no documented trace/correlation header on responses.
- GAP-HIE-008 — OTP error codes/messages not enumerated ("expired" detected by text).
- GAP-HIE-009 — whether ECCIF appears as a scheme in eligibility for every member.
- GAP-HIE-010 — the outcome of an unanswered `POST /claims/visit` cannot be queried by our reference.
