"""Facility Registry lookups (P3-SHA-01; DESIGN §15; KE-DHA-04).

``GET /facilities/search?identifier=&identifier-type=`` returns the registry's view of a
facility: official name, KEPH level, licence, and SHA contract and operational status.
Facility set-up uses it to confirm the FID before SHA traffic starts (the setup screen is
Phase 1's; ``GET /api/v1/interop/facility-registry/`` serves it).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from apps.interop.hie import mapping
from apps.interop.hie.client import HieClient
from apps.interop.hie.client import client as default_client
from apps.interop.hie.errors import HieNotFound

IDENTIFIER_TYPES = ("fid", "fr-code", "mfl", "license-number", "registration-number")


@dataclass(frozen=True)
class FacilityRecord:
    fid: str
    fr_code: str
    official_name: str
    keph_level: str
    licence_status: str
    licence_valid_to: date | None
    sha_contract_status: str
    operational_status: str
    contracted_services: tuple[str, ...]

    @property
    def sha_active(self) -> bool:
        return self.sha_contract_status.lower() == "active" and self.operational_status.lower() in (
            "",
            "operational",
        )


def _record(body: dict[str, Any]) -> FacilityRecord:
    operation = body.get("SHAOperationStatus") or {}
    return FacilityRecord(
        fid=mapping.text(body.get("fidCode")),
        fr_code=mapping.text(body.get("frCode")),
        official_name=mapping.text(body.get("officialName")),
        keph_level=mapping.text(body.get("kephLevel")),
        licence_status=mapping.text(body.get("facilityLicenseStatus")),
        licence_valid_to=mapping.parse_date(body.get("facilityLicenseEndDate")),
        sha_contract_status=mapping.text(body.get("shaContractStatus")),
        operational_status=mapping.text(operation.get("operationalStatus")),
        contracted_services=tuple(mapping.text(s) for s in body.get("shaContractedServices") or []),
    )


def facility_record(
    identifier: str, identifier_type: str = "fid", *, client: HieClient | None = None
) -> FacilityRecord | None:
    """The registry record, or None when the registry has none. Outages raise ``HieError``."""
    if identifier_type not in IDENTIFIER_TYPES:
        raise ValueError(f"identifier_type must be one of {', '.join(IDENTIFIER_TYPES)}")
    hie = client or default_client()
    try:
        body = hie.get(
            "/facilities/search",
            params={"identifier": identifier.strip(), "identifier-type": identifier_type},
            operation="facility_search",
            integration="hie.facility_registry",
        )
    except HieNotFound:
        return None
    return _record(body) if isinstance(body, dict) and body.get("fidCode") else None
