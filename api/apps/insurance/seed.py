"""Seed step: payers, schemes and synthetic cover (IMPLEMENTATION §8; ADR-024 seam).

SHA is the real national payer (the system integrates with it); its schemes carry the
public names. Private insurers and the employer scheme are clearly fictional. Member
numbers are synthetic (``SHA-SYN-…``, ``SYN-A-…``) and attached deterministically to the
synthetic seed patients, so reception, billing and claims have cover to work with.
"""

from typing import Any

from django.db import transaction

from apps.accounts.models import User
from apps.accounts.seed import email_for
from apps.facilities import seed as facility_seed
from apps.insurance import services
from apps.insurance.models import Coverage, Payer, Scheme
from apps.patients.models import Patient

PAYERS = [
    (
        "sha",
        "Social Health Authority (SHA)",
        Payer.Kind.SHA,
        Payer.Gateway.SHA_HIE,
        [
            ("phc", "Primary health care (PHC)", Scheme.Kind.PHC),
            ("shif", "Social Health Insurance Fund (SHIF)", Scheme.Kind.SHIF),
            ("eccif", "Emergency, Chronic and Critical Illness Fund (ECCIF)", Scheme.Kind.ECCIF),
        ],
    ),
    (
        "syn-insurer-a",
        "Synthetic Insurer A",
        Payer.Kind.INSURER,
        Payer.Gateway.SMART,
        [("gold", "Gold corporate cover", Scheme.Kind.CORPORATE)],
    ),
    (
        "syn-insurer-b",
        "Synthetic Insurer B",
        Payer.Kind.INSURER,
        Payer.Gateway.SLADE360,
        [("family", "Family cover", Scheme.Kind.INDIVIDUAL)],
    ),
    (
        "syn-employer",
        "Synthetic Employer Ltd",
        Payer.Kind.EMPLOYER,
        Payer.Gateway.MANUAL,
        [("staff", "Staff medical scheme", Scheme.Kind.CORPORATE)],
    ),
]


def payers_and_schemes() -> dict[str, Scheme]:
    schemes: dict[str, Scheme] = {}
    for code, name, kind, gateway, scheme_rows in PAYERS:
        payer, _ = Payer.objects.get_or_create(
            code=code, defaults={"name": name, "kind": kind, "gateway": gateway}
        )
        for scheme_code, scheme_name, scheme_kind in scheme_rows:
            scheme, _ = Scheme.objects.get_or_create(
                payer=payer, code=scheme_code, defaults={"name": scheme_name, "kind": scheme_kind}
            )
            schemes[f"{code}/{scheme_code}"] = scheme
    return schemes


@transaction.atomic
def run(command: Any) -> None:
    schemes = payers_and_schemes()
    site = facility_seed.facility()
    actor = User.objects.get(email=email_for("receptionist"))  # reception records cover
    added = 0
    patients = Patient.objects.filter(facility=site, is_unidentified=False).order_by("mrn")
    for n, patient in enumerate(patients, start=1):
        wanted = []
        if n % 3 == 0:
            wanted.append((schemes["sha/shif"], f"SHA-SYN-{n:06d}"))
        if n % 10 == 0:
            wanted.append((schemes["syn-insurer-a/gold"], f"SYN-A-{n:05d}"))
        if n % 25 == 0:
            wanted.append((schemes["syn-insurer-b/family"], f"SYN-B-{n:05d}"))
        for scheme, number in wanted:
            if not Coverage.objects.filter(patient=patient, scheme=scheme).exists():
                services.add_coverage(
                    patient=patient, scheme=scheme, member_number=number, actor=actor
                )
                added += 1
    command.stdout.write(f"  insurance: {len(schemes)} schemes, {added} new synthetic coverages")
