// Generated from api/openapi.yaml by `make openapi` — do not edit.

export interface paths {
    "/api/v1/access/approvals/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Requests the user made, or may decide, in the request facility (services enforce rights). */
        get: operations["v1_access_approvals_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/access/approvals/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Requests the user made, or may decide, in the request facility (services enforce rights). */
        get: operations["v1_access_approvals_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/access/approvals/{id}/approve/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Requests the user made, or may decide, in the request facility (services enforce rights). */
        post: operations["v1_access_approvals_approve_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/access/approvals/{id}/reject/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Requests the user made, or may decide, in the request facility (services enforce rights). */
        post: operations["v1_access_approvals_reject_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/access/assignments/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_access_assignments_list"];
        put?: never;
        post: operations["v1_access_assignments_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/access/assignments/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_access_assignments_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/access/assignments/{id}/revoke/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_access_assignments_revoke_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/access/break-glass/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description The break-glass review queue (medical superintendent, DPO); viewing it is audited. */
        get: operations["v1_access_break_glass_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/access/break-glass/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description The break-glass review queue (medical superintendent, DPO); viewing it is audited. */
        get: operations["v1_access_break_glass_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/access/break-glass/{id}/end/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description The clinician leaves emergency access early (their own grant only). */
        post: operations["v1_access_break_glass_end_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/access/break-glass/{id}/review/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description The break-glass review queue (medical superintendent, DPO); viewing it is audited. */
        post: operations["v1_access_break_glass_review_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/access/roles/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_access_roles_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/access/roles/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_access_roles_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/accounts/licences/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_accounts_licences_list"];
        put?: never;
        post: operations["v1_accounts_licences_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/accounts/licences/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_accounts_licences_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["v1_accounts_licences_partial_update"];
        trace?: never;
    };
    "/api/v1/accounts/licences/{id}/verify/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_accounts_licences_verify_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/accounts/profiles/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_accounts_profiles_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/accounts/profiles/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_accounts_profiles_retrieve"];
        put: operations["v1_accounts_profiles_update"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["v1_accounts_profiles_partial_update"];
        trace?: never;
    };
    "/api/v1/accounts/users/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_accounts_users_list"];
        put?: never;
        post: operations["v1_accounts_users_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/accounts/users/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_accounts_users_retrieve"];
        put: operations["v1_accounts_users_update"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["v1_accounts_users_partial_update"];
        trace?: never;
    };
    "/api/v1/accounts/users/{id}/deactivate/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_accounts_users_deactivate_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/accounts/users/{id}/reset-credentials/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Returns a one-time temporary password for the administrator to hand over in person. */
        post: operations["v1_accounts_users_reset_credentials_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/accounts/users/{id}/unlock/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_accounts_users_unlock_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/accounts/users/me/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_accounts_users_me_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai/assistant/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_ai_assistant_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai/forecast/{warehouse_id}/{product_id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_ai_forecast_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai/ocr-intake/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_ai_ocr_intake_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai/redistribution-suggestions/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_ai_redistribution_suggestions_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/analytics/inventory-alerts/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Low-stock alerts for the stores of the request's facility (plain list for legacy dashboards). */
        get: operations["v1_analytics_inventory_alerts_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/audit/events/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_audit_events_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/audit/events/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_audit_events_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/csrf": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_auth_csrf_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/lock": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Lock this workstation now ("lock and switch user"). */
        post: operations["v1_auth_lock_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_auth_login_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_auth_logout_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/mfa/recovery-codes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Replace recovery codes (old unused codes stop working). */
        post: operations["v1_auth_mfa_recovery_codes_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/mfa/totp/confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_auth_mfa_totp_confirm_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/mfa/totp/setup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Start enrolling an authenticator app; returns the otpauth URI once. */
        post: operations["v1_auth_mfa_totp_setup_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/mfa/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Second step of sign-in, or re-verification of a signed-in session. */
        post: operations["v1_auth_mfa_verify_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_auth_password_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/pin": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Set or change the workstation PIN (needs the account password). */
        post: operations["v1_auth_pin_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/switch": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Another user takes over the locked workstation with their PIN. */
        post: operations["v1_auth_switch_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/unlock": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_auth_unlock_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/documents/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description A patient's current documents, shaped by chart access (sensitive ones as placeholders). */
        get: operations["v1_documents_list"];
        put?: never;
        post: operations["v1_documents_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/documents/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_documents_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/documents/{id}/content/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_documents_content_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/facilities/beds/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        get: operations["v1_facilities_beds_list"];
        put?: never;
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        post: operations["v1_facilities_beds_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/facilities/beds/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        get: operations["v1_facilities_beds_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        patch: operations["v1_facilities_beds_partial_update"];
        trace?: never;
    };
    "/api/v1/facilities/beds/{id}/status/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        post: operations["v1_facilities_beds_status_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/facilities/departments/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        get: operations["v1_facilities_departments_list"];
        put?: never;
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        post: operations["v1_facilities_departments_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/facilities/departments/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        get: operations["v1_facilities_departments_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        patch: operations["v1_facilities_departments_partial_update"];
        trace?: never;
    };
    "/api/v1/facilities/facilities/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Facilities the user holds a role in; identifiers and settings edited by facility admins. */
        get: operations["v1_facilities_facilities_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/facilities/facilities/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Facilities the user holds a role in; identifiers and settings edited by facility admins. */
        get: operations["v1_facilities_facilities_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** @description Facilities the user holds a role in; identifiers and settings edited by facility admins. */
        patch: operations["v1_facilities_facilities_partial_update"];
        trace?: never;
    };
    "/api/v1/facilities/service-points/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        get: operations["v1_facilities_service_points_list"];
        put?: never;
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        post: operations["v1_facilities_service_points_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/facilities/service-points/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        get: operations["v1_facilities_service_points_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        patch: operations["v1_facilities_service_points_partial_update"];
        trace?: never;
    };
    "/api/v1/facilities/wards/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        get: operations["v1_facilities_wards_list"];
        put?: never;
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        post: operations["v1_facilities_wards_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/facilities/wards/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        get: operations["v1_facilities_wards_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** @description Shared behaviour: scoped to the request facility; PATCH {active} (de)activates. */
        patch: operations["v1_facilities_wards_partial_update"];
        trace?: never;
    };
    "/api/v1/facility-ops/alerts/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_facility_ops_alerts_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/facility-ops/stats/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_facility_ops_stats_list"];
        put?: never;
        post: operations["v1_facility_ops_stats_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_me_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me/facility": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Switch the active facility (workspace) for this session. */
        post: operations["v1_me_facility_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_patients_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Demographics (name, identifiers, contacts, next of kin) with the access banner. */
        get: operations["v1_patients_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["v1_patients_partial_update"];
        trace?: never;
    };
    "/api/v1/patients/{id}/break-glass/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Emergency full access for a limited time; reviewed afterwards (DESIGN §7.8). */
        post: operations["v1_patients_break_glass_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/{id}/chart/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description The clinical record, shaped by the chart access level (summary, full, sensitive). */
        get: operations["v1_patients_chart_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/{id}/consents/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Record a privacy-notice acknowledgement or a consent decision (append-only). */
        post: operations["v1_patients_consents_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/{id}/contacts/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_patients_contacts_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/{id}/identifiers/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_patients_identifiers_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/{id}/merge/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Request merging ``duplicate`` into this record (an HRIO supervisor approves). */
        post: operations["v1_patients_merge_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/{id}/next-of-kin/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_patients_next_of_kin_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/dsar/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description The DSAR register (DPO, HRIO): due dates, identity checks, exports and outcomes. */
        get: operations["v1_patients_dsar_list"];
        put?: never;
        /** @description The DSAR register (DPO, HRIO): due dates, identity checks, exports and outcomes. */
        post: operations["v1_patients_dsar_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/dsar/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description The DSAR register (DPO, HRIO): due dates, identity checks, exports and outcomes. */
        get: operations["v1_patients_dsar_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/dsar/{id}/close/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description The DSAR register (DPO, HRIO): due dates, identity checks, exports and outcomes. */
        post: operations["v1_patients_dsar_close_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/dsar/{id}/download/{copy}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Stream the JSON or PDF copy produced for this request (audited as a document view). */
        get: operations["v1_patients_dsar_download_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/dsar/{id}/export/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Produce the JSON (FHIR-shaped) and PDF copies for an access or portability request. */
        post: operations["v1_patients_dsar_export_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/dsar/{id}/verify-identity/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description The DSAR register (DPO, HRIO): due dates, identity checks, exports and outcomes. */
        post: operations["v1_patients_dsar_verify_identity_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/merges/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_patients_merges_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/merges/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_patients_merges_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/merges/{id}/unmerge/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_patients_merges_unmerge_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/privacy-notice/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description The notice reception gives at registration; its version goes with the acknowledgement. */
        get: operations["v1_patients_privacy_notice_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/registry-import/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Create a local record from a registry match; the CR ID is stored verified. */
        post: operations["v1_patients_registry_import_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/registry-search/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * @description Local matches first, then the national Client Registry (P1-PAT-02). POST, so the
         *     document number never appears in a URL.
         */
        post: operations["v1_patients_registry_search_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/search/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Search-before-create. POST, so the terms never appear in a URL or access log. */
        post: operations["v1_patients_search_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/patients/unidentified/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["v1_patients_unidentified_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/categories/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Audit catalogue changes on the acting facility's chain. */
        get: operations["v1_products_categories_list"];
        put?: never;
        /** @description Audit catalogue changes on the acting facility's chain. */
        post: operations["v1_products_categories_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/categories/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Audit catalogue changes on the acting facility's chain. */
        get: operations["v1_products_categories_retrieve"];
        /** @description Audit catalogue changes on the acting facility's chain. */
        put: operations["v1_products_categories_update"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** @description Audit catalogue changes on the acting facility's chain. */
        patch: operations["v1_products_categories_partial_update"];
        trace?: never;
    };
    "/api/v1/products/inventory/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Stock levels in the stores of the request's facility. */
        get: operations["v1_products_inventory_list"];
        put?: never;
        /** @description Stock levels in the stores of the request's facility. */
        post: operations["v1_products_inventory_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/inventory/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Stock levels in the stores of the request's facility. */
        get: operations["v1_products_inventory_retrieve"];
        /** @description Stock levels in the stores of the request's facility. */
        put: operations["v1_products_inventory_update"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** @description Stock levels in the stores of the request's facility. */
        patch: operations["v1_products_inventory_partial_update"];
        trace?: never;
    };
    "/api/v1/products/products/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Audit catalogue changes on the acting facility's chain. */
        get: operations["v1_products_products_list"];
        put?: never;
        /** @description Audit catalogue changes on the acting facility's chain. */
        post: operations["v1_products_products_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/products/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Audit catalogue changes on the acting facility's chain. */
        get: operations["v1_products_products_retrieve"];
        /** @description Audit catalogue changes on the acting facility's chain. */
        put: operations["v1_products_products_update"];
        post?: never;
        /** @description Audit catalogue changes on the acting facility's chain. */
        delete: operations["v1_products_products_destroy"];
        options?: never;
        head?: never;
        /** @description Audit catalogue changes on the acting facility's chain. */
        patch: operations["v1_products_products_partial_update"];
        trace?: never;
    };
    "/api/v1/products/products/{product_pk}/images/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_products_products_images_list"];
        put?: never;
        post: operations["v1_products_products_images_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/products/{product_pk}/images/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_products_products_images_retrieve"];
        put?: never;
        post?: never;
        delete: operations["v1_products_products_images_destroy"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/alerts/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Non-PHI public API for integrators: hashed API keys, service-account role, throttled. */
        get: operations["v1_public_alerts_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/facilities/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Non-PHI public API for integrators: hashed API keys, service-account role, throttled. */
        get: operations["v1_public_facilities_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/facility-stats/{facility_id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Non-PHI public API for integrators: hashed API keys, service-account role, throttled. */
        get: operations["v1_public_facility_stats_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/warehouses/bins/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_warehouses_bins_list"];
        put?: never;
        post: operations["v1_warehouses_bins_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/warehouses/bins/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_warehouses_bins_retrieve"];
        put: operations["v1_warehouses_bins_update"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["v1_warehouses_bins_partial_update"];
        trace?: never;
    };
    "/api/v1/warehouses/branches/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description The organisation unit behind the facility. New branches come with new facilities. */
        get: operations["v1_warehouses_branches_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/warehouses/branches/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description The organisation unit behind the facility. New branches come with new facilities. */
        get: operations["v1_warehouses_branches_retrieve"];
        /** @description The organisation unit behind the facility. New branches come with new facilities. */
        put: operations["v1_warehouses_branches_update"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** @description The organisation unit behind the facility. New branches come with new facilities. */
        patch: operations["v1_warehouses_branches_partial_update"];
        trace?: never;
    };
    "/api/v1/warehouses/transfers/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Transfers are records: created, approved by someone else, received — never edited. */
        get: operations["v1_warehouses_transfers_list"];
        put?: never;
        /** @description Transfers are records: created, approved by someone else, received — never edited. */
        post: operations["v1_warehouses_transfers_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/warehouses/transfers/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Transfers are records: created, approved by someone else, received — never edited. */
        get: operations["v1_warehouses_transfers_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/warehouses/transfers/{id}/approve/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Transfers are records: created, approved by someone else, received — never edited. */
        post: operations["v1_warehouses_transfers_approve_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/warehouses/transfers/{id}/complete/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Transfers are records: created, approved by someone else, received — never edited. */
        post: operations["v1_warehouses_transfers_complete_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/warehouses/warehouses/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_warehouses_warehouses_list"];
        put?: never;
        post: operations["v1_warehouses_warehouses_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/warehouses/warehouses/{id}/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["v1_warehouses_warehouses_retrieve"];
        put: operations["v1_warehouses_warehouses_update"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch: operations["v1_warehouses_warehouses_partial_update"];
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** @description The chart access decision the UI shows (selectors.access_payload). */
        Access: {
            level: components["schemas"]["ChartCareTeamEnum"];
            care_team: boolean;
            break_glass: components["schemas"]["BreakGlassAccess"] | null;
            break_glass_available: boolean;
        };
        /**
         * @description * `understaffed` - Understaffed
         *     * `low_footfall` - Low Footfall
         *     * `overcrowded` - Overcrowded
         *     * `stockout_risk` - Stock-Out Risk
         *     * `custom` - Custom
         * @enum {string}
         */
        AlertTypeEnum: "understaffed" | "low_footfall" | "overcrowded" | "stockout_risk" | "custom";
        Approval: {
            /** Format: uuid */
            readonly id: string;
            /** @description Executor key, e.g. access.assignment.grant */
            readonly action: string;
            /** @description Permission codes, one approval needed per entry */
            readonly required_permissions: unknown;
            /** Format: decimal */
            readonly amount: string | null;
            readonly threshold_band: string;
            readonly resource_type: string;
            readonly resource_id: string;
            readonly reason: string;
            readonly status: components["schemas"]["ApprovalStatusEnum"];
            readonly requested_by: number;
            /** Format: date-time */
            readonly requested_at: string;
            /** Format: date-time */
            readonly expires_at: string;
            /** Format: date-time */
            readonly decided_at: string | null;
        };
        /**
         * @description * `pending` - Pending
         *     * `approved` - Approved
         *     * `rejected` - Rejected
         *     * `expired` - Expired
         *     * `cancelled` - Cancelled
         *     * `invalidated` - Invalidated
         * @enum {string}
         */
        ApprovalStatusEnum: "pending" | "approved" | "rejected" | "expired" | "cancelled" | "invalidated";
        Assignment: {
            readonly id: number;
            user: number;
            role: string;
            department?: number | null;
            ward?: number | null;
            /** Format: date-time */
            valid_from?: string;
            /** Format: date-time */
            valid_to?: string | null;
            readonly status: components["schemas"]["AssignmentStatusEnum"];
            reason: string;
            readonly granted_by: number | null;
            readonly approved_by: number | null;
            /** Format: uuid */
            readonly approval: string | null;
            /** Format: date-time */
            readonly revoked_at: string | null;
        };
        AssignmentRequest: {
            user: number;
            role: string;
            department?: number | null;
            ward?: number | null;
            /** Format: date-time */
            valid_from?: string;
            /** Format: date-time */
            valid_to?: string | null;
            reason: string;
        };
        /**
         * @description * `pending_approval` - Pending approval
         *     * `active` - Active
         *     * `rejected` - Rejected
         *     * `revoked` - Revoked
         * @enum {string}
         */
        AssignmentStatusEnum: "pending_approval" | "active" | "rejected" | "revoked";
        AuditEvent: {
            /** Format: uuid */
            readonly id: string;
            /** Format: date-time */
            readonly ts: string;
            /** @description 0 for system-level events */
            readonly facility_id: number;
            readonly seq: number;
            readonly actor_id: number | null;
            readonly actor_role: string;
            readonly workstation_id: string;
            readonly ip: string | null;
            readonly request_id: string;
            readonly action: string;
            readonly resource_type: string;
            readonly resource_id: string;
            /** Format: uuid */
            readonly patient_id: string | null;
            readonly purpose: string;
            readonly outcome: components["schemas"]["AuditEventOutcomeEnum"];
            readonly severity: string;
            readonly detail: unknown;
            readonly hash: string;
        };
        /**
         * @description * `success` - Success
         *     * `denied` - Denied
         *     * `failure` - Failure
         * @enum {string}
         */
        AuditEventOutcomeEnum: "success" | "denied" | "failure";
        Bed: {
            readonly id: number;
            ward: number;
            code: string;
            readonly status: components["schemas"]["StatusCcdEnum"];
            active?: boolean;
            /** Format: date-time */
            readonly status_changed_at: string | null;
        };
        BedRequest: {
            ward: number;
            code: string;
            active?: boolean;
        };
        BedStatus: {
            status: components["schemas"]["StatusCcdEnum"];
        };
        BedStatusRequest: {
            status: components["schemas"]["StatusCcdEnum"];
        };
        BinLocation: {
            readonly id: number;
            readonly warehouse_name: string;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
            is_active?: boolean;
            name: string;
            bin_type?: components["schemas"]["BinTypeEnum"];
            barcode?: string;
            /** Format: uri */
            qr_code?: string | null;
            /** @description Max items that can be stored */
            capacity?: number | null;
            notes?: string;
            warehouse: number;
        };
        BinLocationRequest: {
            is_active?: boolean;
            name: string;
            bin_type?: components["schemas"]["BinTypeEnum"];
            barcode?: string;
            /** Format: binary */
            qr_code?: string;
            /** @description Max items that can be stored */
            capacity?: number | null;
            notes?: string;
            warehouse: number;
        };
        /**
         * @description * `SHELF` - Shelf
         *     * `PALLET` - Pallet
         *     * `BIN` - Storage Bin
         *     * `ROOM` - Storage Room
         * @enum {string}
         */
        BinTypeEnum: "SHELF" | "PALLET" | "BIN" | "ROOM";
        Branch: {
            readonly id: number;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
            name: string;
            code: string;
            kra_pin: string;
            /** Business Registration Number */
            business_reg_no: string;
            /** VAT Number */
            vat_no?: string;
            county: components["schemas"]["CountyEnum"];
            physical_address: string;
            postal_address?: string;
            contact_phone: string;
            contact_email?: string;
            is_active?: boolean;
            manager?: number | null;
        };
        BranchRequest: {
            name: string;
            code: string;
            kra_pin: string;
            /** Business Registration Number */
            business_reg_no: string;
            /** VAT Number */
            vat_no?: string;
            county: components["schemas"]["CountyEnum"];
            physical_address: string;
            postal_address?: string;
            contact_phone: string;
            contact_email?: string;
            is_active?: boolean;
            manager?: number | null;
        };
        BreakGlass: {
            /** Format: uuid */
            readonly id: string;
            readonly user: number;
            readonly user_name: string;
            /** Format: uuid */
            readonly patient: string;
            readonly reason: components["schemas"]["ReasonEnum"];
            readonly justification: string;
            /** Format: date-time */
            readonly granted_at: string;
            /** Format: date-time */
            readonly expires_at: string;
            /** Format: date-time */
            readonly ended_at: string | null;
            readonly review_status: components["schemas"]["ReviewStatusEnum"];
            readonly reviewed_by: number | null;
            /** Format: date-time */
            readonly reviewed_at: string | null;
            readonly review_note: string;
        };
        BreakGlassAccess: {
            /** Format: uuid */
            id: string;
            reason: string;
            /** Format: date-time */
            expires_at: string;
        };
        BreakGlassEnded: {
            /** Format: uuid */
            readonly id: string;
            /** Format: date-time */
            readonly ended_at: string | null;
        };
        BreakGlassGrant: {
            /** Format: uuid */
            readonly id: string;
            /** Format: uuid */
            readonly patient: string;
            readonly reason: components["schemas"]["ReasonEnum"];
            /** Format: date-time */
            readonly granted_at: string;
            /** Format: date-time */
            readonly expires_at: string;
            /** Format: date-time */
            readonly ended_at: string | null;
            readonly review_status: components["schemas"]["ReviewStatusEnum"];
        };
        BreakGlassRequestRequest: {
            reason: components["schemas"]["ReasonEnum"];
            justification: string;
        };
        BreakGlassReview: {
            outcome: components["schemas"]["BreakGlassReviewOutcomeEnum"];
            /** @default  */
            note: string;
        };
        /**
         * @description * `justified` - justified
         *     * `escalated` - escalated
         * @enum {string}
         */
        BreakGlassReviewOutcomeEnum: "justified" | "escalated";
        BreakGlassReviewRequest: {
            outcome: components["schemas"]["BreakGlassReviewOutcomeEnum"];
            /** @default  */
            note: string;
        };
        Category: {
            readonly id: number;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
            is_active?: boolean;
            name: string;
            description?: string;
            vat_category?: components["schemas"]["VatCategoryEnum"];
        };
        /**
         * @description * `lab_report` - Lab report
         *     * `imaging_report` - Imaging report
         *     * `consent_form` - Consent form
         *     * `claim_attachment` - Claim attachment
         *     * `invoice_pdf` - Invoice
         *     * `receipt_pdf` - Receipt
         *     * `claim_form` - Claim form
         *     * `discharge_summary` - Discharge summary
         *     * `referral_letter` - Referral letter
         *     * `id_scan` - Identity document scan
         *     * `dsar_export` - Data subject request export
         *     * `audit_anchor` - Audit anchor
         *     * `other` - Other
         * @enum {string}
         */
        CategoryEnum: "lab_report" | "imaging_report" | "consent_form" | "claim_attachment" | "invoice_pdf" | "receipt_pdf" | "claim_form" | "discharge_summary" | "referral_letter" | "id_scan" | "dsar_export" | "audit_anchor" | "other";
        CategoryRequest: {
            is_active?: boolean;
            name: string;
            description?: string;
            vat_category?: components["schemas"]["VatCategoryEnum"];
        };
        /**
         * @description * `in_person` - In person
         *     * `email` - E-mail
         *     * `letter` - Letter
         *     * `phone` - Phone
         * @enum {string}
         */
        ChannelEnum: "in_person" | "email" | "letter" | "phone";
        /** @description Sections are ``null`` below their level; Phase 2 fills them (selectors.chart_sections). */
        Chart: {
            access: components["schemas"]["Access"];
            patient: components["schemas"]["Patient"];
            summary: {
                [key: string]: unknown;
            } | null;
            record: {
                [key: string]: unknown;
            } | null;
        };
        /**
         * @description * `none` - none
         *     * `demographics` - demographics
         *     * `summary` - summary
         *     * `full` - full
         *     * `sensitive` - sensitive
         * @enum {string}
         */
        ChartCareTeamEnum: "none" | "demographics" | "summary" | "full" | "sensitive";
        Consent: {
            /** Format: uuid */
            readonly id: string;
            readonly kind: components["schemas"]["KindA36Enum"];
            readonly decision: components["schemas"]["DecisionEnum"];
            readonly version: string;
            readonly method: components["schemas"]["MethodEnum"];
            readonly given_by: components["schemas"]["GivenByEnum"];
            /** Format: date-time */
            readonly recorded_at: string;
            readonly recorded_by: number;
        };
        ConsentInputRequest: {
            /** @default  */
            version: string;
            method: components["schemas"]["MethodEnum"];
            /** @default patient */
            given_by: components["schemas"]["GivenByEnum"];
            kind: components["schemas"]["KindA36Enum"];
            decision: components["schemas"]["DecisionEnum"];
        };
        Contact: {
            /** Format: uuid */
            readonly id: string;
            kind: components["schemas"]["KindA4cEnum"];
            value: string;
            is_primary?: boolean;
            readonly active: boolean;
        };
        ContactInputRequest: {
            kind: components["schemas"]["KindA4cEnum"];
            value: string;
            /** @default false */
            is_primary: boolean;
        };
        /**
         * @description * `MOMBASA` - Mombasa
         *     * `KWALE` - Kwale
         *     * `KILIFI` - Kilifi
         *     * `TANA_RIVER` - Tana River
         *     * `LAMU` - Lamu
         *     * `TAITA_TAVETA` - Taita Taveta
         *     * `GARISSA` - Garissa
         *     * `WAJIR` - Wajir
         *     * `MANDERA` - Mandera
         *     * `MARSABIT` - Marsabit
         *     * `ISIOLO` - Isiolo
         *     * `MERU` - Meru
         *     * `THARAKA_NITHI` - Tharaka Nithi
         *     * `EMBU` - Embu
         *     * `KITUI` - Kitui
         *     * `MACHAKOS` - Machakos
         *     * `MAKUENI` - Makueni
         *     * `NYANDARUA` - Nyandarua
         *     * `NYERI` - Nyeri
         *     * `KIRINYAGA` - Kirinyaga
         *     * `MURANGA` - Murang'a
         *     * `KIAMBU` - Kiambu
         *     * `TURKANA` - Turkana
         *     * `WEST_POKOT` - West Pokot
         *     * `SAMBURU` - Samburu
         *     * `TRANS_NZOIA` - Trans Nzoia
         *     * `UASIN_GISHU` - Uasin Gishu
         *     * `ELGEYO_MARAKWET` - Elgeyo Marakwet
         *     * `NANDI` - Nandi
         *     * `BARINGO` - Baringo
         *     * `LAIKIPIA` - Laikipia
         *     * `NAKURU` - Nakuru
         *     * `NAROK` - Narok
         *     * `KAJIADO` - Kajiado
         *     * `KERICHO` - Kericho
         *     * `BOMET` - Bomet
         *     * `KAKAMEGA` - Kakamega
         *     * `VIHIGA` - Vihiga
         *     * `BUNGOMA` - Bungoma
         *     * `BUSIA` - Busia
         *     * `SIAYA` - Siaya
         *     * `KISUMU` - Kisumu
         *     * `HOMA_BAY` - Homa Bay
         *     * `MIGORI` - Migori
         *     * `KISII` - Kisii
         *     * `NYAMIRA` - Nyamira
         *     * `NAIROBI` - Nairobi
         * @enum {string}
         */
        CountyEnum: "MOMBASA" | "KWALE" | "KILIFI" | "TANA_RIVER" | "LAMU" | "TAITA_TAVETA" | "GARISSA" | "WAJIR" | "MANDERA" | "MARSABIT" | "ISIOLO" | "MERU" | "THARAKA_NITHI" | "EMBU" | "KITUI" | "MACHAKOS" | "MAKUENI" | "NYANDARUA" | "NYERI" | "KIRINYAGA" | "MURANGA" | "KIAMBU" | "TURKANA" | "WEST_POKOT" | "SAMBURU" | "TRANS_NZOIA" | "UASIN_GISHU" | "ELGEYO_MARAKWET" | "NANDI" | "BARINGO" | "LAIKIPIA" | "NAKURU" | "NAROK" | "KAJIADO" | "KERICHO" | "BOMET" | "KAKAMEGA" | "VIHIGA" | "BUNGOMA" | "BUSIA" | "SIAYA" | "KISUMU" | "HOMA_BAY" | "MIGORI" | "KISII" | "NYAMIRA" | "NAIROBI";
        Decision: {
            /** @default  */
            comment: string;
        };
        /**
         * @description * `given` - Given
         *     * `declined` - Declined
         *     * `withdrawn` - Withdrawn
         * @enum {string}
         */
        DecisionEnum: "given" | "declined" | "withdrawn";
        DecisionRequest: {
            /** @default  */
            comment: string;
        };
        Department: {
            readonly id: number;
            code: string;
            name: string;
            active?: boolean;
        };
        DepartmentRequest: {
            code: string;
            name: string;
            active?: boolean;
        };
        Document: {
            /** Format: uuid */
            readonly id: string;
            /** Format: uuid */
            readonly patient: string | null;
            readonly category: components["schemas"]["CategoryEnum"];
            readonly sensitivity: components["schemas"]["SensitivityEnum"];
            readonly content_type: string;
            readonly size: number;
            readonly filename: string;
            readonly storage_backend: components["schemas"]["StorageBackendEnum"];
            readonly uploaded_by: number | null;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: uuid */
            readonly superseded_by: string | null;
            /** Format: date */
            readonly retention_until: string | null;
            readonly legal_hold: boolean;
        };
        Dsar: {
            /** Format: uuid */
            readonly id: string;
            readonly reference: string;
            /** Format: uuid */
            readonly patient: string;
            readonly kind: components["schemas"]["DsarKindEnum"];
            readonly channel: components["schemas"]["ChannelEnum"];
            readonly requester: components["schemas"]["RequesterEnum"];
            readonly details: string;
            /** Format: date-time */
            readonly received_at: string;
            /** Format: date-time */
            readonly due_at: string;
            readonly overdue: boolean;
            readonly status: components["schemas"]["DsarStatusEnum"];
            readonly identity_verified_by: number | null;
            /** Format: date-time */
            readonly identity_verified_at: string | null;
            readonly identity_evidence: string;
            /** Format: uuid */
            readonly export_json: string | null;
            /** Format: uuid */
            readonly export_pdf: string | null;
            readonly outcome: string;
            /** Format: date-time */
            readonly closed_at: string | null;
            readonly closed_by: number | null;
            readonly version: number;
        };
        DsarClose: {
            status: components["schemas"]["DsarCloseStatusEnum"];
            /** @default  */
            outcome: string;
        };
        DsarCloseRequest: {
            status: components["schemas"]["DsarCloseStatusEnum"];
            /** @default  */
            outcome: string;
        };
        /**
         * @description * `completed` - completed
         *     * `refused` - refused
         *     * `withdrawn` - withdrawn
         * @enum {string}
         */
        DsarCloseStatusEnum: "completed" | "refused" | "withdrawn";
        DsarExport: {
            /** @default false */
            include_sensitive: boolean;
        };
        DsarExportRequest: {
            /** @default false */
            include_sensitive: boolean;
        };
        /**
         * @description * `access` - Access
         *     * `correction` - Correction
         *     * `deletion` - Deletion
         *     * `objection` - Objection
         *     * `restriction` - Restriction
         *     * `portability` - Portability
         * @enum {string}
         */
        DsarKindEnum: "access" | "correction" | "deletion" | "objection" | "restriction" | "portability";
        /**
         * @description * `received` - Received
         *     * `verified` - Identity verified
         *     * `completed` - Completed
         *     * `refused` - Refused with reasons
         *     * `withdrawn` - Withdrawn
         * @enum {string}
         */
        DsarStatusEnum: "received" | "verified" | "completed" | "refused" | "withdrawn";
        DsarVerify: {
            evidence: components["schemas"]["EvidenceEnum"];
        };
        DsarVerifyRequest: {
            evidence: components["schemas"]["EvidenceEnum"];
        };
        /**
         * @description * `birth_certificate_seen` - birth_certificate_seen
         *     * `known_to_staff` - known_to_staff
         *     * `national_id_seen` - national_id_seen
         *     * `other_document_seen` - other_document_seen
         *     * `passport_seen` - passport_seen
         * @enum {string}
         */
        EvidenceEnum: "birth_certificate_seen" | "known_to_staff" | "national_id_seen" | "other_document_seen" | "passport_seen";
        Facility: {
            readonly id: number;
            name: string;
            /** KMHFL MFL code */
            mfl_code?: (string | null) | string;
            /** Facility Registry ID */
            fid?: (string | null) | string;
            keph_level?: components["schemas"]["KephLevelEnum"] | components["schemas"]["NullEnum"];
            sha_contract_number?: string;
            kra_pin?: string;
            /** ODPC registration (controller) */
            odpc_controller_registration?: string;
            /** ODPC registration of the system vendor/host (processor) */
            odpc_processor_registration?: string;
            slade_provider_code?: string;
            /** @description Placeholders: {MFL}, {YY}, {YYYY}, {seq} (gap-free per facility per year) */
            mrn_format?: string;
            require_mfa_for_all?: boolean;
            workstation_lock_minutes?: number;
            session_idle_minutes?: number;
            session_absolute_hours?: number;
            care_team_expiry_hours?: number;
            break_glass_minutes?: number;
            readonly active: boolean;
        };
        FacilityAlert: {
            readonly id: number;
            /** Health Facility */
            warehouse: number;
            readonly warehouse_name: string;
            alert_type: components["schemas"]["AlertTypeEnum"];
            /** @description Gemma-generated or manually entered narrative */
            message: string;
            severity?: components["schemas"]["SeverityEnum"];
            resolved?: boolean;
            /** Format: date-time */
            readonly resolved_at: string | null;
            /** Format: date-time */
            readonly created_at: string;
        };
        FacilityChoice: {
            facility: number;
        };
        FacilityChoiceRequest: {
            facility: number;
        };
        FacilityDailyStats: {
            readonly id: number;
            /** Health Facility */
            warehouse: number;
            readonly warehouse_name: string;
            /** Format: date */
            date: string;
            patient_footfall?: number;
            beds_total?: number;
            beds_occupied?: number;
            doctors_scheduled?: number;
            doctors_present?: number;
            readonly bed_occupancy_rate: string;
            readonly attendance_rate: string;
        };
        FacilityDailyStatsRequest: {
            /** Health Facility */
            warehouse: number;
            /** Format: date */
            date: string;
            patient_footfall?: number;
            beds_total?: number;
            beds_occupied?: number;
            doctors_scheduled?: number;
            doctors_present?: number;
        };
        /**
         * @description * `patient` - The patient
         *     * `guardian` - Parent or guardian
         *     * `representative` - Next of kin or representative
         * @enum {string}
         */
        GivenByEnum: "patient" | "guardian" | "representative";
        Identifier: {
            /** Format: uuid */
            readonly id: string;
            type: components["schemas"]["Type7a8Enum"];
            value: string;
            /** @description Issuing country for passports */
            issuer?: string;
            readonly source: components["schemas"]["SourceEnum"];
            /** Format: date-time */
            readonly verified_at: string | null;
            readonly active: boolean;
        };
        IdentifierInputRequest: {
            type: string;
            value: string;
            /** @default  */
            issuer: string;
        };
        Inventory: {
            readonly id: number;
            readonly product_name: string;
            readonly warehouse_name: string;
            readonly needs_restock: boolean;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
            is_active?: boolean;
            quantity?: number;
            /** Format: date-time */
            readonly last_checked: string;
            product: number;
            warehouse: number;
        };
        InventoryRequest: {
            is_active?: boolean;
            quantity?: number;
            product: number;
            warehouse: number;
        };
        /**
         * @description * `2` - Level 2 — dispensary
         *     * `3` - Level 3 — health centre
         *     * `4` - Level 4 — sub-county hospital / medical centre
         *     * `5` - Level 5 — county referral hospital
         *     * `6` - Level 6 — national referral hospital
         * @enum {integer}
         */
        KephLevelEnum: 2 | 3 | 4 | 5 | 6;
        /**
         * @description * `privacy_notice` - Privacy notice acknowledged
         *     * `sms_reminders` - SMS reminders
         *     * `research` - Research use
         * @enum {string}
         */
        KindA36Enum: "privacy_notice" | "sms_reminders" | "research";
        /**
         * @description * `phone` - Phone
         *     * `email` - E-mail
         * @enum {string}
         */
        KindA4cEnum: "phone" | "email";
        Licence: {
            readonly id: number;
            user: number;
            regulator: components["schemas"]["RegulatorEnum"];
            registration_number: string;
            licence_number?: string;
            /** Format: date */
            valid_from?: string | null;
            /** Format: date */
            valid_to: string;
            /** Health Worker Registry PUID */
            readonly puid: string;
            slade_code?: string;
            /** Format: date-time */
            readonly verified_at: string | null;
            readonly verification_source: string;
            active?: boolean;
        };
        LicenceRequest: {
            user: number;
            regulator: components["schemas"]["RegulatorEnum"];
            registration_number: string;
            licence_number?: string;
            /** Format: date */
            valid_from?: string | null;
            /** Format: date */
            valid_to: string;
            slade_code?: string;
            active?: boolean;
        };
        Login: {
            /** Format: email */
            email: string;
        };
        LoginRequest: {
            /** Format: email */
            email: string;
            password: string;
        };
        MaskedIdentifier: {
            type: components["schemas"]["Type7a8Enum"];
            readonly value: string;
        };
        Merge: {
            /** Format: uuid */
            readonly id: string;
            /** Format: uuid */
            readonly survivor: string;
            /** Format: uuid */
            readonly duplicate: string;
            readonly status: components["schemas"]["MergeStatusEnum"];
            readonly reason: string;
            /** Format: uuid */
            readonly approval: string | null;
            /** Format: uuid */
            readonly reversal_approval: string | null;
            /** Format: date-time */
            readonly merged_at: string | null;
            /** Format: date-time */
            readonly reversed_at: string | null;
        };
        MergeRequestRequest: {
            /** Format: uuid */
            duplicate: string;
            reason: string;
        };
        /**
         * @description * `requested` - Waiting for approval
         *     * `merged` - Merged
         *     * `reversed` - Reversed
         * @enum {string}
         */
        MergeStatusEnum: "requested" | "merged" | "reversed";
        /**
         * @description * `verbal` - Read out / explained
         *     * `printed` - Printed notice given
         *     * `electronic` - Shown on screen or sent electronically
         * @enum {string}
         */
        MethodEnum: "verbal" | "printed" | "electronic";
        MfaCode: {
            code?: string;
            recovery_code?: string;
        };
        MfaCodeRequest: {
            code?: string;
            recovery_code?: string;
        };
        NextOfKin: {
            /** Format: uuid */
            readonly id: string;
            name: string;
            relationship: string;
            phone?: string;
            readonly active: boolean;
        };
        NextOfKinInputRequest: {
            name: string;
            relationship: string;
            /** @default  */
            phone: string;
        };
        NullEnum: null;
        PaginatedApprovalList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Approval"][];
        };
        PaginatedAssignmentList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Assignment"][];
        };
        PaginatedAuditEventList: {
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?cursor=cD00ODY%3D"
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?cursor=cj0xJnA9NDg3
             */
            previous?: string | null;
            results: components["schemas"]["AuditEvent"][];
        };
        PaginatedBedList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Bed"][];
        };
        PaginatedBinLocationList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["BinLocation"][];
        };
        PaginatedBranchList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Branch"][];
        };
        PaginatedBreakGlassList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["BreakGlass"][];
        };
        PaginatedCategoryList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Category"][];
        };
        PaginatedDepartmentList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Department"][];
        };
        PaginatedDocumentList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Document"][];
        };
        PaginatedDsarList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Dsar"][];
        };
        PaginatedFacilityList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Facility"][];
        };
        PaginatedInventoryList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Inventory"][];
        };
        PaginatedLicenceList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Licence"][];
        };
        PaginatedMergeList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Merge"][];
        };
        PaginatedProductImageList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["ProductImage"][];
        };
        PaginatedProductList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Product"][];
        };
        PaginatedServicePointList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["ServicePoint"][];
        };
        PaginatedStockTransferList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["StockTransfer"][];
        };
        PaginatedUserList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["User"][];
        };
        PaginatedWardList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Ward"][];
        };
        PaginatedWarehouseList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["Warehouse"][];
        };
        PaginatedWorkerProfileList: {
            /** @example 123 */
            count: number;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=4
             */
            next?: string | null;
            /**
             * Format: uri
             * @example http://api.example.org/accounts/?page=2
             */
            previous?: string | null;
            results: components["schemas"]["WorkerProfile"][];
        };
        PasswordChangeRequest: {
            current_password: string;
            new_password: string;
        };
        PatchedBedRequest: {
            ward?: number;
            code?: string;
            active?: boolean;
        };
        PatchedBinLocationRequest: {
            is_active?: boolean;
            name?: string;
            bin_type?: components["schemas"]["BinTypeEnum"];
            barcode?: string;
            /** Format: binary */
            qr_code?: string;
            /** @description Max items that can be stored */
            capacity?: number | null;
            notes?: string;
            warehouse?: number;
        };
        PatchedBranchRequest: {
            name?: string;
            code?: string;
            kra_pin?: string;
            /** Business Registration Number */
            business_reg_no?: string;
            /** VAT Number */
            vat_no?: string;
            county?: components["schemas"]["CountyEnum"];
            physical_address?: string;
            postal_address?: string;
            contact_phone?: string;
            contact_email?: string;
            is_active?: boolean;
            manager?: number | null;
        };
        PatchedCategoryRequest: {
            is_active?: boolean;
            name?: string;
            description?: string;
            vat_category?: components["schemas"]["VatCategoryEnum"];
        };
        PatchedDepartmentRequest: {
            code?: string;
            name?: string;
            active?: boolean;
        };
        PatchedFacilityRequest: {
            name?: string;
            /** KMHFL MFL code */
            mfl_code?: (string | null) | string;
            /** Facility Registry ID */
            fid?: (string | null) | string;
            keph_level?: components["schemas"]["KephLevelEnum"] | components["schemas"]["NullEnum"];
            sha_contract_number?: string;
            kra_pin?: string;
            /** ODPC registration (controller) */
            odpc_controller_registration?: string;
            /** ODPC registration of the system vendor/host (processor) */
            odpc_processor_registration?: string;
            slade_provider_code?: string;
            /** @description Placeholders: {MFL}, {YY}, {YYYY}, {seq} (gap-free per facility per year) */
            mrn_format?: string;
            require_mfa_for_all?: boolean;
            workstation_lock_minutes?: number;
            session_idle_minutes?: number;
            session_absolute_hours?: number;
            care_team_expiry_hours?: number;
            break_glass_minutes?: number;
        };
        PatchedInventoryRequest: {
            is_active?: boolean;
            quantity?: number;
            product?: number;
            warehouse?: number;
        };
        PatchedLicenceRequest: {
            user?: number;
            regulator?: components["schemas"]["RegulatorEnum"];
            registration_number?: string;
            licence_number?: string;
            /** Format: date */
            valid_from?: string | null;
            /** Format: date */
            valid_to?: string;
            slade_code?: string;
            active?: boolean;
        };
        PatchedPatientUpdateRequest: {
            version?: number;
            given_name?: string;
            middle_name?: string;
            family_name?: string;
            sex?: components["schemas"]["SexD10Enum"];
            /** Format: date */
            date_of_birth?: string | null;
            dob_estimated?: boolean;
        };
        PatchedProductRequest: {
            name?: string;
            short_name?: string;
            /** @description EAN-13, UPC, or custom barcode */
            barcode?: string;
            product_type?: components["schemas"]["ProductTypeEnum"];
            /** Format: decimal */
            buying_price?: string;
            /** Format: decimal */
            selling_price?: string;
            /**
             * Format: decimal
             * @description Bulk purchase price
             */
            wholesale_price?: string | null;
            /** Minimum Safe Stock */
            reorder_level?: number;
            is_active?: boolean;
            category?: number;
        };
        PatchedServicePointRequest: {
            code?: string;
            name?: string;
            kind?: components["schemas"]["ServicePointKindEnum"];
            department?: number | null;
            active?: boolean;
        };
        PatchedUserRequest: {
            /**
             * Email address
             * Format: email
             */
            email?: string;
            first_name?: string;
            last_name?: string;
            phone?: (string | null) | string;
            role?: components["schemas"]["RoleEnum"];
            is_approved?: boolean;
        };
        PatchedWardRequest: {
            code?: string;
            name?: string;
            kind?: components["schemas"]["WardKindEnum"];
            sex?: components["schemas"]["WardSexEnum"];
            department?: number | null;
            active?: boolean;
        };
        PatchedWarehouseRequest: {
            is_active?: boolean;
            name?: string;
            code?: string;
            warehouse_type?: components["schemas"]["WarehouseTypeEnum"];
            physical_address?: string;
            contact_phone?: string;
            /** @description Total capacity in cubic meters */
            capacity?: number | null;
            temperature_controlled?: boolean;
            temperature_range?: string;
            branch?: number;
            manager?: number | null;
        };
        PatchedWorkerProfileRequest: {
            id_number?: string;
            /** Format: binary */
            signature?: string;
            is_active?: boolean;
            branch?: number;
            /** @description Facility assignment for Tier-2 scoped dashboards and AI endpoints. */
            warehouse?: number | null;
        };
        Patient: {
            /** Format: uuid */
            readonly id: string;
            /** Medical record number */
            readonly mrn: string;
            readonly given_name: string;
            readonly middle_name: string;
            readonly family_name: string;
            readonly display_name: string;
            readonly sex: components["schemas"]["SexD10Enum"];
            /** Format: date */
            readonly date_of_birth: string | null;
            readonly dob_estimated: boolean;
            readonly age: string | null;
            readonly is_unidentified: boolean;
            /** @description Placeholder for unidentified patients, e.g. Unknown male, approx. 30y */
            readonly description: string;
            readonly status: components["schemas"]["StatusD33Enum"];
            /** Format: uuid */
            readonly merged_into: string | null;
            readonly version: number;
            readonly identifiers: components["schemas"]["Identifier"][];
            readonly contacts: components["schemas"]["Contact"][];
            readonly next_of_kin: components["schemas"]["NextOfKin"][];
            readonly consents: components["schemas"]["Consent"][];
            /** Format: date */
            readonly retention_until: string | null;
            readonly legal_hold: boolean;
        };
        PatientCreateRequest: {
            given_name: string;
            /** @default  */
            middle_name: string;
            family_name: string;
            sex: components["schemas"]["SexD10Enum"];
            /** Format: date */
            date_of_birth?: string | null;
            age_years?: number | null;
            age_months?: number | null;
            identifiers?: components["schemas"]["IdentifierInputRequest"][];
            contacts?: components["schemas"]["ContactInputRequest"][];
            next_of_kin?: components["schemas"]["NextOfKinInputRequest"][];
            /** @default  */
            override_reason: string;
            privacy_notice: components["schemas"]["PrivacyNoticeRequest"];
        };
        PatientRecord: {
            /** Format: uuid */
            readonly id: string;
            /** Medical record number */
            readonly mrn: string;
            readonly given_name: string;
            readonly middle_name: string;
            readonly family_name: string;
            readonly display_name: string;
            readonly sex: components["schemas"]["SexD10Enum"];
            /** Format: date */
            readonly date_of_birth: string | null;
            readonly dob_estimated: boolean;
            readonly age: string | null;
            readonly is_unidentified: boolean;
            /** @description Placeholder for unidentified patients, e.g. Unknown male, approx. 30y */
            readonly description: string;
            readonly status: components["schemas"]["StatusD33Enum"];
            /** Format: uuid */
            readonly merged_into: string | null;
            readonly version: number;
            readonly identifiers: components["schemas"]["Identifier"][];
            readonly contacts: components["schemas"]["Contact"][];
            readonly next_of_kin: components["schemas"]["NextOfKin"][];
            readonly consents: components["schemas"]["Consent"][];
            /** Format: date */
            readonly retention_until: string | null;
            readonly legal_hold: boolean;
            readonly access: components["schemas"]["Access"];
        };
        Pin: {
            pin: string;
        };
        PinRequest: {
            pin: string;
        };
        PinSet: {
            pin: string;
        };
        PinSetRequest: {
            pin: string;
            password: string;
        };
        PrivacyNoticeRequest: {
            version: string;
            method: components["schemas"]["MethodEnum"];
            /** @default patient */
            given_by: components["schemas"]["GivenByEnum"];
        };
        PrivacyNoticeText: {
            version: string;
            text: string;
        };
        Product: {
            readonly id: number;
            readonly images: components["schemas"]["ProductImage"][];
            readonly category_name: string;
            /** Format: decimal */
            readonly vat_amount: string;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
            name: string;
            short_name?: string;
            readonly sku: string;
            /** @description EAN-13, UPC, or custom barcode */
            barcode?: string;
            product_type?: components["schemas"]["ProductTypeEnum"];
            /** Format: decimal */
            buying_price: string;
            /** Format: decimal */
            selling_price: string;
            /**
             * Format: decimal
             * @description Bulk purchase price
             */
            wholesale_price?: string | null;
            /** Minimum Safe Stock */
            reorder_level?: number;
            is_active?: boolean;
            /** Format: date-time */
            readonly last_restocked: string | null;
            category: number;
        };
        ProductCreate: {
            name: string;
            short_name?: string;
            category: number;
            /** @description EAN-13, UPC, or custom barcode */
            barcode?: string;
            product_type?: components["schemas"]["ProductTypeEnum"];
            /** Format: decimal */
            buying_price: string;
            /** Format: decimal */
            selling_price: string;
            /**
             * Format: decimal
             * @description Bulk purchase price
             */
            wholesale_price?: string | null;
            /** Minimum Safe Stock */
            reorder_level?: number;
        };
        ProductCreateRequest: {
            name: string;
            short_name?: string;
            category: number;
            /** @description EAN-13, UPC, or custom barcode */
            barcode?: string;
            product_type?: components["schemas"]["ProductTypeEnum"];
            /** Format: decimal */
            buying_price: string;
            /** Format: decimal */
            selling_price: string;
            /**
             * Format: decimal
             * @description Bulk purchase price
             */
            wholesale_price?: string | null;
            /** Minimum Safe Stock */
            reorder_level?: number;
        };
        ProductImage: {
            readonly id: number;
            /**
             * Format: uri
             * @description Optimal size: 800x800px
             */
            image: string;
            is_primary?: boolean;
            caption?: string;
        };
        ProductImageRequest: {
            /**
             * Format: binary
             * @description Optimal size: 800x800px
             */
            image: string;
            is_primary?: boolean;
            caption?: string;
        };
        ProductRequest: {
            name: string;
            short_name?: string;
            /** @description EAN-13, UPC, or custom barcode */
            barcode?: string;
            product_type?: components["schemas"]["ProductTypeEnum"];
            /** Format: decimal */
            buying_price: string;
            /** Format: decimal */
            selling_price: string;
            /**
             * Format: decimal
             * @description Bulk purchase price
             */
            wholesale_price?: string | null;
            /** Minimum Safe Stock */
            reorder_level?: number;
            is_active?: boolean;
            category: number;
        };
        /**
         * @description * `PHYSICAL` - Physical Product
         *     * `DIGITAL` - Digital Product
         *     * `SERVICE` - Service
         * @enum {string}
         */
        ProductTypeEnum: "PHYSICAL" | "DIGITAL" | "SERVICE";
        RTInventoryAlert: {
            readonly id: number;
            product: number;
            readonly product_name: string;
            warehouse: number;
            readonly warehouse_name: string;
            current_stock: number;
            resolved?: boolean;
            /** Format: date-time */
            readonly created_at: string;
        };
        Reason: {
            reason: string;
        };
        /**
         * @description * `emergency` - Emergency
         *     * `continuity_of_care` - Continuity of care
         *     * `clinical_review` - Clinical review
         * @enum {string}
         */
        ReasonEnum: "emergency" | "continuity_of_care" | "clinical_review";
        ReasonRequest: {
            reason: string;
        };
        RegistryImportRequest: {
            type: components["schemas"]["Type9c6Enum"];
            number: string;
            privacy_notice: components["schemas"]["PrivacyNoticeRequest"];
            contacts?: components["schemas"]["ContactInputRequest"][];
            next_of_kin?: components["schemas"]["NextOfKinInputRequest"][];
            /** @default  */
            override_reason: string;
        };
        /** @description What reception sees to confirm identity: names and DOB, identifiers and phone masked. */
        RegistryPerson: {
            cr_id: string;
            given_name: string;
            middle_name: string;
            family_name: string;
            sex: string;
            /** Format: date */
            date_of_birth: string | null;
            readonly identifiers: components["schemas"]["MaskedIdentifier"][];
            readonly phone: string;
        };
        RegistryQueryRequest: {
            type: components["schemas"]["Type9c6Enum"];
            number: string;
        };
        RegistryResult: {
            status: components["schemas"]["RegistryResultStatusEnum"];
            person: components["schemas"]["RegistryPerson"] | null;
            /** Format: uuid */
            registered_patient: string | null;
        };
        /**
         * @description * `found` - found
         *     * `not_found` - not_found
         *     * `unavailable` - unavailable
         * @enum {string}
         */
        RegistryResultStatusEnum: "found" | "not_found" | "unavailable";
        RegistrySearch: {
            local: components["schemas"]["SearchResult"][];
            registry: components["schemas"]["RegistryResult"];
        };
        /**
         * @description * `KMPDC` - Kenya Medical Practitioners and Dentists Council
         *     * `COC` - Clinical Officers Council
         *     * `NCK` - Nursing Council of Kenya
         *     * `PPB` - Pharmacy and Poisons Board
         *     * `KMLTTB` - Kenya Medical Laboratory Technicians and Technologists Board
         *     * `OTHER` - Other regulator
         * @enum {string}
         */
        RegulatorEnum: "KMPDC" | "COC" | "NCK" | "PPB" | "KMLTTB" | "OTHER";
        /**
         * @description * `patient` - The patient
         *     * `guardian` - Parent or guardian
         *     * `representative` - Authorised representative
         * @enum {string}
         */
        RequesterEnum: "patient" | "guardian" | "representative";
        /**
         * @description * `pending` - Awaiting review
         *     * `justified` - Justified
         *     * `escalated` - Escalated
         * @enum {string}
         */
        ReviewStatusEnum: "pending" | "justified" | "escalated";
        Revoke: {
            reason: string;
        };
        RevokeRequest: {
            reason: string;
        };
        Role: {
            readonly id: number;
            readonly code: string;
            readonly name: string;
            readonly description: string;
            /** @description Granting it needs a second facility admin */
            readonly privileged: boolean;
            readonly mfa_required: boolean;
            /** @description Supervisor add-on assigned on top of a base role */
            readonly addon: boolean;
            readonly requires_cosign: boolean;
            readonly chart_baseline: components["schemas"]["ChartCareTeamEnum"];
            readonly chart_care_team: components["schemas"]["ChartCareTeamEnum"];
            /** @description Regulators whose licence covers licensed permissions */
            readonly licence_regulators: unknown;
            readonly permissions: string[];
        };
        /**
         * @description * `ADMIN` - System Administrator
         *     * `BRANCH_MANAGER` - Branch Manager
         *     * `PROCUREMENT` - Procurement Officer
         *     * `WAREHOUSE` - Warehouse Staff
         *     * `CASHIER` - Cashier
         *     * `REPORTER` - Reports Viewer
         * @enum {string}
         */
        RoleEnum: "ADMIN" | "BRANCH_MANAGER" | "PROCUREMENT" | "WAREHOUSE" | "CASHIER" | "REPORTER";
        /**
         * @description Search terms travel in the body, never the URL: names, IDs and phones would
         *     otherwise land in proxy access logs (ADR-023).
         */
        SearchQueryRequest: {
            q: string;
            /** Format: date */
            date_of_birth?: string;
            sex?: components["schemas"]["SexD10Enum"];
        };
        SearchResponse: {
            results: components["schemas"]["SearchResult"][];
        };
        SearchResult: {
            /** Format: uuid */
            id: string;
            mrn: string;
            display_name: string;
            sex: string;
            /** Format: date */
            date_of_birth: string;
            dob_estimated: boolean;
            readonly age: string | null;
            is_unidentified: boolean;
            readonly identifiers: components["schemas"]["MaskedIdentifier"][];
            score: number;
            reasons: string[];
        };
        /**
         * @description * `normal` - Not sensitive
         *     * `hiv` - HIV and PrEP
         *     * `mental_health` - Mental health
         *     * `sexual_reproductive` - Sexual and reproductive health
         *     * `gbv` - Gender-based violence and post-rape care
         *     * `substance_use` - Substance use
         *     * `genetic` - Genetic results
         * @enum {string}
         */
        SensitivityEnum: "normal" | "hiv" | "mental_health" | "sexual_reproductive" | "gbv" | "substance_use" | "genetic";
        ServicePoint: {
            readonly id: number;
            code: string;
            name: string;
            kind: components["schemas"]["ServicePointKindEnum"];
            department?: number | null;
            active?: boolean;
        };
        /**
         * @description * `reception` - Reception
         *     * `triage` - Triage
         *     * `consultation` - Consultation room
         *     * `emergency` - Emergency / resuscitation
         *     * `lab` - Laboratory
         *     * `imaging` - Imaging
         *     * `pharmacy` - Pharmacy
         *     * `cashier` - Cashier
         *     * `treatment_room` - Treatment / procedure room
         *     * `ward_station` - Ward station
         *     * `records` - Health records
         *     * `other` - Other
         * @enum {string}
         */
        ServicePointKindEnum: "reception" | "triage" | "consultation" | "emergency" | "lab" | "imaging" | "pharmacy" | "cashier" | "treatment_room" | "ward_station" | "records" | "other";
        ServicePointRequest: {
            code: string;
            name: string;
            kind: components["schemas"]["ServicePointKindEnum"];
            department?: number | null;
            active?: boolean;
        };
        /**
         * @description * `low` - Low
         *     * `medium` - Medium
         *     * `high` - High
         * @enum {string}
         */
        SeverityEnum: "low" | "medium" | "high";
        /**
         * @description * `female` - Female
         *     * `male` - Male
         *     * `intersex` - Intersex
         *     * `unknown` - Unknown
         * @enum {string}
         */
        SexD10Enum: "female" | "male" | "intersex" | "unknown";
        /**
         * @description * `manual` - Entered by staff
         *     * `client_registry` - HIE Client Registry
         *     * `system` - Generated by the system
         * @enum {string}
         */
        SourceEnum: "manual" | "client_registry" | "system";
        /**
         * @description * `available` - Available
         *     * `occupied` - Occupied
         *     * `cleaning` - Cleaning
         *     * `out_of_service` - Out of service
         * @enum {string}
         */
        StatusCcdEnum: "available" | "occupied" | "cleaning" | "out_of_service";
        /**
         * @description * `active` - Active
         *     * `merged` - Merged into another record
         * @enum {string}
         */
        StatusD33Enum: "active" | "merged";
        StockTransfer: {
            readonly id: number;
            readonly product_name: string;
            readonly from_warehouse_name: string;
            readonly to_warehouse_name: string;
            readonly initiated_by_name: string;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
            is_active?: boolean;
            readonly reference_no: string;
            transfer_type?: components["schemas"]["TransferTypeEnum"];
            quantity: number;
            status?: components["schemas"]["StockTransferStatusEnum"];
            delivery_note?: string;
            transporter?: string;
            transporter_license?: string;
            notes?: string;
            /** Format: date-time */
            readonly verified_at: string | null;
            product: number;
            from_warehouse: number;
            to_warehouse: number;
            from_bin?: number | null;
            to_bin?: number | null;
            readonly initiated_by: number;
            approved_by?: number | null;
        };
        StockTransferCreate: {
            product: number;
            transfer_type?: components["schemas"]["TransferTypeEnum"];
            from_warehouse: number;
            to_warehouse: number;
            from_bin?: number | null;
            to_bin?: number | null;
            quantity: number;
            notes?: string;
        };
        StockTransferCreateRequest: {
            product: number;
            transfer_type?: components["schemas"]["TransferTypeEnum"];
            from_warehouse: number;
            to_warehouse: number;
            from_bin?: number | null;
            to_bin?: number | null;
            quantity: number;
            notes?: string;
        };
        StockTransferRequest: {
            is_active?: boolean;
            transfer_type?: components["schemas"]["TransferTypeEnum"];
            quantity: number;
            status?: components["schemas"]["StockTransferStatusEnum"];
            delivery_note?: string;
            transporter?: string;
            transporter_license?: string;
            notes?: string;
            product: number;
            from_warehouse: number;
            to_warehouse: number;
            from_bin?: number | null;
            to_bin?: number | null;
            approved_by?: number | null;
        };
        /**
         * @description * `PENDING` - Pending Approval
         *     * `APPROVED` - Approved
         *     * `IN_TRANSIT` - In Transit
         *     * `RECEIVED` - Received
         *     * `VERIFIED` - Verified
         *     * `CANCELLED` - Cancelled
         * @enum {string}
         */
        StockTransferStatusEnum: "PENDING" | "APPROVED" | "IN_TRANSIT" | "RECEIVED" | "VERIFIED" | "CANCELLED";
        /**
         * @description * `local` - Local (data/)
         *     * `s3` - S3-compatible bucket
         * @enum {string}
         */
        StorageBackendEnum: "local" | "s3";
        Switch: {
            pin: string;
            /** Format: email */
            email: string;
        };
        SwitchRequest: {
            pin: string;
            /** Format: email */
            email: string;
        };
        /**
         * @description * `INTERNAL` - Internal Transfer
         *     * `SUPPLIER` - Supplier Delivery
         *     * `CUSTOMER` - Customer Return
         *     * `DAMAGED` - Damaged Goods
         * @enum {string}
         */
        TransferTypeEnum: "INTERNAL" | "SUPPLIER" | "CUSTOMER" | "DAMAGED";
        /**
         * @description * `cr_id` - HIE Client Registry ID
         *     * `sha_number` - SHA number
         *     * `national_id` - National ID
         *     * `maisha_namba` - Maisha Namba
         *     * `alien_id` - Alien ID
         *     * `refugee_id` - Refugee ID
         *     * `passport` - Passport
         *     * `birth_certificate` - Birth certificate
         *     * `birth_notification` - Birth notification
         *     * `temporary` - Temporary ID (unidentified patient)
         * @enum {string}
         */
        Type7a8Enum: "cr_id" | "sha_number" | "national_id" | "maisha_namba" | "alien_id" | "refugee_id" | "passport" | "birth_certificate" | "birth_notification" | "temporary";
        /**
         * @description * `national_id` - national_id
         *     * `maisha_namba` - maisha_namba
         *     * `alien_id` - alien_id
         *     * `refugee_id` - refugee_id
         * @enum {string}
         */
        Type9c6Enum: "national_id" | "maisha_namba" | "alien_id" | "refugee_id";
        UnidentifiedRequest: {
            sex: components["schemas"]["SexD10Enum"];
            approx_age_years?: number | null;
        };
        Unmerge: {
            reason: string;
        };
        UnmergeRequest: {
            reason: string;
        };
        User: {
            readonly id: number;
            /**
             * Email address
             * Format: email
             */
            email: string;
            first_name?: string;
            last_name?: string;
            phone?: (string | null) | string;
            role?: components["schemas"]["RoleEnum"];
            is_approved?: boolean;
            /**
             * Active
             * @description Designates whether this user should be treated as active. Unselect this instead of deleting accounts.
             */
            readonly is_active: boolean;
            readonly account_locked: boolean;
            readonly must_change_password: boolean;
            readonly mfa_enrolled: boolean;
            /** @description Active role codes at the request's facility (for the administration screens). */
            readonly roles: string[];
            /** Format: date-time */
            readonly last_login: string | null;
            /** Format: date-time */
            readonly date_joined: string;
        };
        UserCreate: {
            /**
             * Email address
             * Format: email
             */
            email: string;
            first_name?: string;
            last_name?: string;
            phone?: (string | null) | string;
            role?: components["schemas"]["RoleEnum"];
            is_approved?: boolean;
        };
        UserCreateRequest: {
            /**
             * Email address
             * Format: email
             */
            email: string;
            password?: string;
            first_name?: string;
            last_name?: string;
            phone?: (string | null) | string;
            role?: components["schemas"]["RoleEnum"];
            is_approved?: boolean;
        };
        UserRequest: {
            /**
             * Email address
             * Format: email
             */
            email: string;
            first_name?: string;
            last_name?: string;
            phone?: (string | null) | string;
            role?: components["schemas"]["RoleEnum"];
            is_approved?: boolean;
        };
        /**
         * @description * `STANDARD` - Standard Rate (16%)
         *     * `ZERO` - Zero Rated (0%)
         *     * `EXEMPT` - Exempt
         * @enum {string}
         */
        VatCategoryEnum: "STANDARD" | "ZERO" | "EXEMPT";
        Ward: {
            readonly id: number;
            code: string;
            name: string;
            kind?: components["schemas"]["WardKindEnum"];
            sex?: components["schemas"]["WardSexEnum"];
            department?: number | null;
            active?: boolean;
            readonly beds_total: number;
            readonly beds_available: number;
        };
        /**
         * @description * `general` - General
         *     * `maternity` - Maternity
         *     * `paediatric` - Paediatric
         *     * `newborn` - Newborn unit
         *     * `icu` - ICU
         *     * `hdu` - HDU
         *     * `isolation` - Isolation
         *     * `surgical` - Surgical
         * @enum {string}
         */
        WardKindEnum: "general" | "maternity" | "paediatric" | "newborn" | "icu" | "hdu" | "isolation" | "surgical";
        WardRequest: {
            code: string;
            name: string;
            kind?: components["schemas"]["WardKindEnum"];
            sex?: components["schemas"]["WardSexEnum"];
            department?: number | null;
            active?: boolean;
        };
        /**
         * @description * `female` - Female
         *     * `male` - Male
         *     * `mixed` - Mixed
         * @enum {string}
         */
        WardSexEnum: "female" | "male" | "mixed";
        Warehouse: {
            readonly id: number;
            readonly branch_name: string;
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
            is_active?: boolean;
            name: string;
            code: string;
            warehouse_type?: components["schemas"]["WarehouseTypeEnum"];
            physical_address: string;
            contact_phone: string;
            /** @description Total capacity in cubic meters */
            capacity?: number | null;
            temperature_controlled?: boolean;
            temperature_range?: string;
            branch: number;
            manager?: number | null;
        };
        WarehouseRequest: {
            is_active?: boolean;
            name: string;
            code: string;
            warehouse_type?: components["schemas"]["WarehouseTypeEnum"];
            physical_address: string;
            contact_phone: string;
            /** @description Total capacity in cubic meters */
            capacity?: number | null;
            temperature_controlled?: boolean;
            temperature_range?: string;
            branch: number;
            manager?: number | null;
        };
        /**
         * @description * `DRY` - Dry Goods
         *     * `COLD` - Cold Storage
         *     * `FROZEN` - Frozen Goods
         *     * `HAZARD` - Hazardous Materials
         * @enum {string}
         */
        WarehouseTypeEnum: "DRY" | "COLD" | "FROZEN" | "HAZARD";
        WorkerProfile: {
            readonly id: number;
            readonly user: components["schemas"]["User"];
            /** Format: date-time */
            readonly created_at: string;
            /** Format: date-time */
            readonly updated_at: string;
            id_number?: string;
            /** Format: uri */
            signature?: string | null;
            is_active?: boolean;
            branch: number;
            /** @description Facility assignment for Tier-2 scoped dashboards and AI endpoints. */
            warehouse?: number | null;
        };
        WorkerProfileRequest: {
            id_number?: string;
            /** Format: binary */
            signature?: string;
            is_active?: boolean;
            branch: number;
            /** @description Facility assignment for Tier-2 scoped dashboards and AI endpoints. */
            warehouse?: number | null;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    v1_access_approvals_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedApprovalList"];
                };
            };
        };
    };
    v1_access_approvals_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this approval request. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Approval"];
                };
            };
        };
    };
    v1_access_approvals_approve_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this approval request. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["DecisionRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["DecisionRequest"];
                "multipart/form-data": components["schemas"]["DecisionRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Decision"];
                };
            };
        };
    };
    v1_access_approvals_reject_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this approval request. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["DecisionRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["DecisionRequest"];
                "multipart/form-data": components["schemas"]["DecisionRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Decision"];
                };
            };
        };
    };
    v1_access_assignments_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedAssignmentList"];
                };
            };
        };
    };
    v1_access_assignments_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssignmentRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["AssignmentRequest"];
                "multipart/form-data": components["schemas"]["AssignmentRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Assignment"];
                };
            };
        };
    };
    v1_access_assignments_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this role assignment. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Assignment"];
                };
            };
        };
    };
    v1_access_assignments_revoke_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this role assignment. */
                id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RevokeRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["RevokeRequest"];
                "multipart/form-data": components["schemas"]["RevokeRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Revoke"];
                };
            };
        };
    };
    v1_access_break_glass_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedBreakGlassList"];
                };
            };
        };
    };
    v1_access_break_glass_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this break glass grant. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BreakGlass"];
                };
            };
        };
    };
    v1_access_break_glass_end_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this break glass grant. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BreakGlassEnded"];
                };
            };
        };
    };
    v1_access_break_glass_review_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this break glass grant. */
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BreakGlassReviewRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["BreakGlassReviewRequest"];
                "multipart/form-data": components["schemas"]["BreakGlassReviewRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BreakGlassReview"];
                };
            };
        };
    };
    v1_access_roles_list: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Role"][];
                };
            };
        };
    };
    v1_access_roles_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this role. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Role"];
                };
            };
        };
    };
    v1_accounts_licences_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedLicenceList"];
                };
            };
        };
    };
    v1_accounts_licences_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LicenceRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["LicenceRequest"];
                "multipart/form-data": components["schemas"]["LicenceRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Licence"];
                };
            };
        };
    };
    v1_accounts_licences_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this professional licence. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Licence"];
                };
            };
        };
    };
    v1_accounts_licences_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this professional licence. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedLicenceRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedLicenceRequest"];
                "multipart/form-data": components["schemas"]["PatchedLicenceRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Licence"];
                };
            };
        };
    };
    v1_accounts_licences_verify_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this professional licence. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Licence"];
                };
            };
        };
    };
    v1_accounts_profiles_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedWorkerProfileList"];
                };
            };
        };
    };
    v1_accounts_profiles_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this worker profile. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkerProfile"];
                };
            };
        };
    };
    v1_accounts_profiles_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this worker profile. */
                id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkerProfileRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["WorkerProfileRequest"];
                "multipart/form-data": components["schemas"]["WorkerProfileRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkerProfile"];
                };
            };
        };
    };
    v1_accounts_profiles_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this worker profile. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedWorkerProfileRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedWorkerProfileRequest"];
                "multipart/form-data": components["schemas"]["PatchedWorkerProfileRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkerProfile"];
                };
            };
        };
    };
    v1_accounts_users_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedUserList"];
                };
            };
        };
    };
    v1_accounts_users_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserCreateRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["UserCreateRequest"];
                "multipart/form-data": components["schemas"]["UserCreateRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserCreate"];
                };
            };
        };
    };
    v1_accounts_users_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this user. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["User"];
                };
            };
        };
    };
    v1_accounts_users_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this user. */
                id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["UserRequest"];
                "multipart/form-data": components["schemas"]["UserRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["User"];
                };
            };
        };
    };
    v1_accounts_users_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this user. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedUserRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedUserRequest"];
                "multipart/form-data": components["schemas"]["PatchedUserRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["User"];
                };
            };
        };
    };
    v1_accounts_users_deactivate_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this user. */
                id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReasonRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["ReasonRequest"];
                "multipart/form-data": components["schemas"]["ReasonRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Reason"];
                };
            };
        };
    };
    v1_accounts_users_reset_credentials_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this user. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["User"];
                };
            };
        };
    };
    v1_accounts_users_unlock_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this user. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["User"];
                };
            };
        };
    };
    v1_accounts_users_me_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["User"];
                };
            };
        };
    };
    v1_ai_assistant_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_ai_forecast_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: number;
                warehouse_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_ai_ocr_intake_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_ai_redistribution_suggestions_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_analytics_inventory_alerts_list: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RTInventoryAlert"][];
                };
            };
        };
    };
    v1_audit_events_list: {
        parameters: {
            query?: {
                /** @description The pagination cursor value. */
                cursor?: string;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedAuditEventList"];
                };
            };
        };
    };
    v1_audit_events_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this audit event. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuditEvent"];
                };
            };
        };
    };
    v1_auth_csrf_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_auth_lock_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_auth_login_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["LoginRequest"];
                "multipart/form-data": components["schemas"]["LoginRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Login"];
                };
            };
        };
    };
    v1_auth_logout_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_auth_mfa_recovery_codes_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_auth_mfa_totp_confirm_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["MfaCodeRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["MfaCodeRequest"];
                "multipart/form-data": components["schemas"]["MfaCodeRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MfaCode"];
                };
            };
        };
    };
    v1_auth_mfa_totp_setup_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_auth_mfa_verify_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["MfaCodeRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["MfaCodeRequest"];
                "multipart/form-data": components["schemas"]["MfaCodeRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MfaCode"];
                };
            };
        };
    };
    v1_auth_password_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordChangeRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PasswordChangeRequest"];
                "multipart/form-data": components["schemas"]["PasswordChangeRequest"];
            };
        };
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_auth_pin_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PinSetRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PinSetRequest"];
                "multipart/form-data": components["schemas"]["PinSetRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PinSet"];
                };
            };
        };
    };
    v1_auth_switch_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SwitchRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["SwitchRequest"];
                "multipart/form-data": components["schemas"]["SwitchRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Switch"];
                };
            };
        };
    };
    v1_auth_unlock_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PinRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PinRequest"];
                "multipart/form-data": components["schemas"]["PinRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Pin"];
                };
            };
        };
    };
    v1_documents_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedDocumentList"];
                };
            };
        };
    };
    v1_documents_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Document"];
                };
            };
        };
    };
    v1_documents_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this document. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Document"];
                };
            };
        };
    };
    v1_documents_content_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this document. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Document"];
                };
            };
        };
    };
    v1_facilities_beds_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedBedList"];
                };
            };
        };
    };
    v1_facilities_beds_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BedRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["BedRequest"];
                "multipart/form-data": components["schemas"]["BedRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Bed"];
                };
            };
        };
    };
    v1_facilities_beds_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this bed. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Bed"];
                };
            };
        };
    };
    v1_facilities_beds_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this bed. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedBedRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedBedRequest"];
                "multipart/form-data": components["schemas"]["PatchedBedRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Bed"];
                };
            };
        };
    };
    v1_facilities_beds_status_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this bed. */
                id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BedStatusRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["BedStatusRequest"];
                "multipart/form-data": components["schemas"]["BedStatusRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BedStatus"];
                };
            };
        };
    };
    v1_facilities_departments_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedDepartmentList"];
                };
            };
        };
    };
    v1_facilities_departments_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DepartmentRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["DepartmentRequest"];
                "multipart/form-data": components["schemas"]["DepartmentRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Department"];
                };
            };
        };
    };
    v1_facilities_departments_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this department. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Department"];
                };
            };
        };
    };
    v1_facilities_departments_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this department. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedDepartmentRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedDepartmentRequest"];
                "multipart/form-data": components["schemas"]["PatchedDepartmentRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Department"];
                };
            };
        };
    };
    v1_facilities_facilities_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedFacilityList"];
                };
            };
        };
    };
    v1_facilities_facilities_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this facility. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Facility"];
                };
            };
        };
    };
    v1_facilities_facilities_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this facility. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedFacilityRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedFacilityRequest"];
                "multipart/form-data": components["schemas"]["PatchedFacilityRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Facility"];
                };
            };
        };
    };
    v1_facilities_service_points_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedServicePointList"];
                };
            };
        };
    };
    v1_facilities_service_points_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ServicePointRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["ServicePointRequest"];
                "multipart/form-data": components["schemas"]["ServicePointRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ServicePoint"];
                };
            };
        };
    };
    v1_facilities_service_points_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this service point. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ServicePoint"];
                };
            };
        };
    };
    v1_facilities_service_points_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this service point. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedServicePointRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedServicePointRequest"];
                "multipart/form-data": components["schemas"]["PatchedServicePointRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ServicePoint"];
                };
            };
        };
    };
    v1_facilities_wards_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedWardList"];
                };
            };
        };
    };
    v1_facilities_wards_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WardRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["WardRequest"];
                "multipart/form-data": components["schemas"]["WardRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Ward"];
                };
            };
        };
    };
    v1_facilities_wards_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this ward. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Ward"];
                };
            };
        };
    };
    v1_facilities_wards_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this ward. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedWardRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedWardRequest"];
                "multipart/form-data": components["schemas"]["PatchedWardRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Ward"];
                };
            };
        };
    };
    v1_facility_ops_alerts_list: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FacilityAlert"][];
                };
            };
        };
    };
    v1_facility_ops_stats_list: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FacilityDailyStats"][];
                };
            };
        };
    };
    v1_facility_ops_stats_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FacilityDailyStatsRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["FacilityDailyStatsRequest"];
                "multipart/form-data": components["schemas"]["FacilityDailyStatsRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FacilityDailyStats"];
                };
            };
        };
    };
    v1_me_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_me_facility_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FacilityChoiceRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["FacilityChoiceRequest"];
                "multipart/form-data": components["schemas"]["FacilityChoiceRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FacilityChoice"];
                };
            };
        };
    };
    v1_patients_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatientCreateRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatientCreateRequest"];
                "multipart/form-data": components["schemas"]["PatientCreateRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Patient"];
                };
            };
        };
    };
    v1_patients_retrieve: {
        parameters: {
            query?: {
                /** @description Why the record is opened; registration and billing see demographics only. */
                purpose?: "audit" | "billing" | "care" | "records" | "registration";
            };
            header?: never;
            path: {
                /** @description A UUID string identifying this patient. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PatientRecord"];
                };
            };
        };
    };
    v1_patients_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this patient. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedPatientUpdateRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedPatientUpdateRequest"];
                "multipart/form-data": components["schemas"]["PatchedPatientUpdateRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Patient"];
                };
            };
        };
    };
    v1_patients_break_glass_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this patient. */
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BreakGlassRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["BreakGlassRequestRequest"];
                "multipart/form-data": components["schemas"]["BreakGlassRequestRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BreakGlassGrant"];
                };
            };
        };
    };
    v1_patients_chart_retrieve: {
        parameters: {
            query?: {
                /** @description Why the record is opened; registration and billing see demographics only. */
                purpose?: "audit" | "billing" | "care" | "records" | "registration";
            };
            header?: never;
            path: {
                /** @description A UUID string identifying this patient. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Chart"];
                };
            };
        };
    };
    v1_patients_consents_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this patient. */
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConsentInputRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["ConsentInputRequest"];
                "multipart/form-data": components["schemas"]["ConsentInputRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Consent"];
                };
            };
        };
    };
    v1_patients_contacts_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this patient. */
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ContactInputRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["ContactInputRequest"];
                "multipart/form-data": components["schemas"]["ContactInputRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Contact"];
                };
            };
        };
    };
    v1_patients_identifiers_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this patient. */
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IdentifierInputRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["IdentifierInputRequest"];
                "multipart/form-data": components["schemas"]["IdentifierInputRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Identifier"];
                };
            };
        };
    };
    v1_patients_merge_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this patient. */
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MergeRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["MergeRequestRequest"];
                "multipart/form-data": components["schemas"]["MergeRequestRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Merge"];
                };
            };
        };
    };
    v1_patients_next_of_kin_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this patient. */
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NextOfKinInputRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["NextOfKinInputRequest"];
                "multipart/form-data": components["schemas"]["NextOfKinInputRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NextOfKin"];
                };
            };
        };
    };
    v1_patients_dsar_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedDsarList"];
                };
            };
        };
    };
    v1_patients_dsar_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Dsar"];
                };
            };
        };
    };
    v1_patients_dsar_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this data subject request. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Dsar"];
                };
            };
        };
    };
    v1_patients_dsar_close_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this data subject request. */
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DsarCloseRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["DsarCloseRequest"];
                "multipart/form-data": components["schemas"]["DsarCloseRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DsarClose"];
                };
            };
        };
    };
    v1_patients_dsar_download_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                copy: string;
                /** @description A UUID string identifying this data subject request. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Dsar"];
                };
            };
        };
    };
    v1_patients_dsar_export_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this data subject request. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["DsarExportRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["DsarExportRequest"];
                "multipart/form-data": components["schemas"]["DsarExportRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DsarExport"];
                };
            };
        };
    };
    v1_patients_dsar_verify_identity_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this data subject request. */
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DsarVerifyRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["DsarVerifyRequest"];
                "multipart/form-data": components["schemas"]["DsarVerifyRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DsarVerify"];
                };
            };
        };
    };
    v1_patients_merges_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedMergeList"];
                };
            };
        };
    };
    v1_patients_merges_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this patient merge. */
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Merge"];
                };
            };
        };
    };
    v1_patients_merges_unmerge_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A UUID string identifying this patient merge. */
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UnmergeRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["UnmergeRequest"];
                "multipart/form-data": components["schemas"]["UnmergeRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Unmerge"];
                };
            };
        };
    };
    v1_patients_privacy_notice_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PrivacyNoticeText"];
                };
            };
        };
    };
    v1_patients_registry_import_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegistryImportRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["RegistryImportRequest"];
                "multipart/form-data": components["schemas"]["RegistryImportRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Patient"];
                };
            };
        };
    };
    v1_patients_registry_search_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegistryQueryRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["RegistryQueryRequest"];
                "multipart/form-data": components["schemas"]["RegistryQueryRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RegistrySearch"];
                };
            };
        };
    };
    v1_patients_search_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SearchQueryRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["SearchQueryRequest"];
                "multipart/form-data": components["schemas"]["SearchQueryRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchResponse"];
                };
            };
        };
    };
    v1_patients_unidentified_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UnidentifiedRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["UnidentifiedRequest"];
                "multipart/form-data": components["schemas"]["UnidentifiedRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Patient"];
                };
            };
        };
    };
    v1_products_categories_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedCategoryList"];
                };
            };
        };
    };
    v1_products_categories_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CategoryRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["CategoryRequest"];
                "multipart/form-data": components["schemas"]["CategoryRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Category"];
                };
            };
        };
    };
    v1_products_categories_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Commodity Category. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Category"];
                };
            };
        };
    };
    v1_products_categories_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Commodity Category. */
                id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CategoryRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["CategoryRequest"];
                "multipart/form-data": components["schemas"]["CategoryRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Category"];
                };
            };
        };
    };
    v1_products_categories_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Commodity Category. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedCategoryRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedCategoryRequest"];
                "multipart/form-data": components["schemas"]["PatchedCategoryRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Category"];
                };
            };
        };
    };
    v1_products_inventory_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedInventoryList"];
                };
            };
        };
    };
    v1_products_inventory_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InventoryRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["InventoryRequest"];
                "multipart/form-data": components["schemas"]["InventoryRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Inventory"];
                };
            };
        };
    };
    v1_products_inventory_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Facility Stock Level. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Inventory"];
                };
            };
        };
    };
    v1_products_inventory_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Facility Stock Level. */
                id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InventoryRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["InventoryRequest"];
                "multipart/form-data": components["schemas"]["InventoryRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Inventory"];
                };
            };
        };
    };
    v1_products_inventory_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Facility Stock Level. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedInventoryRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedInventoryRequest"];
                "multipart/form-data": components["schemas"]["PatchedInventoryRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Inventory"];
                };
            };
        };
    };
    v1_products_products_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedProductList"];
                };
            };
        };
    };
    v1_products_products_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProductCreateRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["ProductCreateRequest"];
                "multipart/form-data": components["schemas"]["ProductCreateRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductCreate"];
                };
            };
        };
    };
    v1_products_products_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Medical Commodity. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Product"];
                };
            };
        };
    };
    v1_products_products_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Medical Commodity. */
                id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProductRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["ProductRequest"];
                "multipart/form-data": components["schemas"]["ProductRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Product"];
                };
            };
        };
    };
    v1_products_products_destroy: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Medical Commodity. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_products_products_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Medical Commodity. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedProductRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedProductRequest"];
                "multipart/form-data": components["schemas"]["PatchedProductRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Product"];
                };
            };
        };
    };
    v1_products_products_images_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path: {
                product_pk: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedProductImageList"];
                };
            };
        };
    };
    v1_products_products_images_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_pk: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProductImageRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["ProductImageRequest"];
                "multipart/form-data": components["schemas"]["ProductImageRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductImage"];
                };
            };
        };
    };
    v1_products_products_images_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this product image. */
                id: number;
                product_pk: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductImage"];
                };
            };
        };
    };
    v1_products_products_images_destroy: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this product image. */
                id: number;
                product_pk: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_public_alerts_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_public_facilities_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_public_facility_stats_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                facility_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    v1_warehouses_bins_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedBinLocationList"];
                };
            };
        };
    };
    v1_warehouses_bins_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BinLocationRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["BinLocationRequest"];
                "multipart/form-data": components["schemas"]["BinLocationRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BinLocation"];
                };
            };
        };
    };
    v1_warehouses_bins_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Bin Location. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BinLocation"];
                };
            };
        };
    };
    v1_warehouses_bins_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Bin Location. */
                id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BinLocationRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["BinLocationRequest"];
                "multipart/form-data": components["schemas"]["BinLocationRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BinLocation"];
                };
            };
        };
    };
    v1_warehouses_bins_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Bin Location. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedBinLocationRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedBinLocationRequest"];
                "multipart/form-data": components["schemas"]["PatchedBinLocationRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BinLocation"];
                };
            };
        };
    };
    v1_warehouses_branches_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedBranchList"];
                };
            };
        };
    };
    v1_warehouses_branches_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this branch. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Branch"];
                };
            };
        };
    };
    v1_warehouses_branches_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this branch. */
                id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BranchRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["BranchRequest"];
                "multipart/form-data": components["schemas"]["BranchRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Branch"];
                };
            };
        };
    };
    v1_warehouses_branches_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this branch. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedBranchRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedBranchRequest"];
                "multipart/form-data": components["schemas"]["PatchedBranchRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Branch"];
                };
            };
        };
    };
    v1_warehouses_transfers_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedStockTransferList"];
                };
            };
        };
    };
    v1_warehouses_transfers_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StockTransferCreateRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["StockTransferCreateRequest"];
                "multipart/form-data": components["schemas"]["StockTransferCreateRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StockTransferCreate"];
                };
            };
        };
    };
    v1_warehouses_transfers_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Stock Transfer. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StockTransfer"];
                };
            };
        };
    };
    v1_warehouses_transfers_approve_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Stock Transfer. */
                id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StockTransferRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["StockTransferRequest"];
                "multipart/form-data": components["schemas"]["StockTransferRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StockTransfer"];
                };
            };
        };
    };
    v1_warehouses_transfers_complete_create: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this Stock Transfer. */
                id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StockTransferRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["StockTransferRequest"];
                "multipart/form-data": components["schemas"]["StockTransferRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StockTransfer"];
                };
            };
        };
    };
    v1_warehouses_warehouses_list: {
        parameters: {
            query?: {
                /** @description A page number within the paginated result set. */
                page?: number;
                /** @description Number of results to return per page. */
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedWarehouseList"];
                };
            };
        };
    };
    v1_warehouses_warehouses_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WarehouseRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["WarehouseRequest"];
                "multipart/form-data": components["schemas"]["WarehouseRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Warehouse"];
                };
            };
        };
    };
    v1_warehouses_warehouses_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this warehouse. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Warehouse"];
                };
            };
        };
    };
    v1_warehouses_warehouses_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this warehouse. */
                id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WarehouseRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["WarehouseRequest"];
                "multipart/form-data": components["schemas"]["WarehouseRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Warehouse"];
                };
            };
        };
    };
    v1_warehouses_warehouses_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description A unique integer value identifying this warehouse. */
                id: number;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedWarehouseRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedWarehouseRequest"];
                "multipart/form-data": components["schemas"]["PatchedWarehouseRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Warehouse"];
                };
            };
        };
    };
}
