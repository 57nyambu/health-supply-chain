"""Slade360 (Savannah Informatics EDI / HealthCloud) — INSURANCE.md §6; ADR-010.

No public API specification: access needs a partner agreement (owner action,
GAP-SLADE-001). ``SLADE360_MODE=fake`` (default) runs ``FakeSlade360Gateway``;
``sandbox``/``live`` refuse to start until the spec and credentials exist. Slade codes are
already stored on ``Facility.slade_provider_code`` and ``ProfessionalLicence.slade_code``.
"""
