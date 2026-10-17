"""Phase 3 lane seed step (ADR-024): synthetic SHA tariffs and cover that exercises every
scripted payer outcome (ADR-073), so the owner can demo each path in fake mode.

Runs after the Phase 1 insurance seed; idempotent. Synthetic only: tariff codes are
``SYN-…``; patients are the seeded synthetic patients (national IDs ``000NNNNN``), chosen
by the last two digits the fakes script on.
"""

from pathlib import Path
from typing import Any

from django.db import transaction

from apps.accounts.models import User
from apps.accounts.seed import email_for
from apps.facilities import seed as facility_seed
from apps.insurance import services, tariffs
from apps.insurance.models import Coverage
from apps.insurance.seed import payers_and_schemes
from apps.patients.models import PatientIdentifier

TARIFF_FILE = Path(__file__).resolve().parent / "fixtures" / "sha_tariffs_synthetic.csv"
TARIFF_LABEL = "SYN-2026-10"

# Last two digits of the national ID → the SHA outcome the fake HIE scripts for it.
SHA_OUTCOMES = {
    "11": "eligible",
    "97": "not found",
    "96": "not eligible",
    "98": "inactive (arrears)",
    "94": "no phone for OTP",
    "93": "fingerprint never matches",
    "92": "no fingerprints, OTP allowed",
    "91": "stuck pending authorisation",
    "90": "biometrics enforced",
}
# Member-number suffix → scripted private-payer outcome.
PRIVATE_OUTCOMES = {"97": "not found", "96": "not eligible", "98": "lapsed", "95": "payer outage"}


@transaction.atomic
def run(command: Any) -> None:
    result = tariffs.import_file(TARIFF_FILE.read_bytes(), label=TARIFF_LABEL, synthetic=True)
    schemes = payers_and_schemes()
    site = facility_seed.facility()
    actor = User.objects.get(email=email_for("receptionist"))
    added = 0
    identifiers = PatientIdentifier.objects.filter(
        facility=site, type=PatientIdentifier.Type.NATIONAL_ID, active=True
    ).select_related("patient")
    by_suffix: dict[str, Any] = {}
    for row in sorted(identifiers, key=lambda r: r.value):  # deterministic choice
        by_suffix.setdefault(row.value[-2:], row.patient)
    for suffix in SHA_OUTCOMES:
        patient = by_suffix.get(suffix)
        if patient is None:
            continue
        if not Coverage.objects.filter(patient=patient, scheme=schemes["sha/shif"]).exists():
            services.add_coverage(
                patient=patient,
                scheme=schemes["sha/shif"],
                member_number=f"SHA-SYN-9{suffix}{patient.mrn[-4:]}",
                actor=actor,
            )
            added += 1
    patient = by_suffix.get("11")
    if patient is not None:
        for suffix in PRIVATE_OUTCOMES:
            for key, prefix in (("syn-insurer-a/gold", "SYN-A"), ("syn-insurer-b/family", "SYN-B")):
                number = f"{prefix}-900{suffix}"
                if not Coverage.objects.filter(
                    patient=patient,
                    scheme=schemes[key],
                    member_number_index=services.member_index(number),
                ).exists():
                    services.add_coverage(
                        patient=patient, scheme=schemes[key], member_number=number, actor=actor
                    )
                    added += 1
    command.stdout.write(
        f"  insurance (phase 3): tariff {result.version.label} ({result.rows} synthetic interventions), "
        f"{added} scripted coverages"
    )
