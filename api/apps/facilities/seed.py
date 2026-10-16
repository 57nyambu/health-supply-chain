"""Seed step: the synthetic facility (test MFL 99999, KEPH 4) and its layout (IMPLEMENTATION §8)."""

from typing import Any

from django.db import transaction

from apps.facilities import services
from apps.facilities.models import Department, Facility, ServicePoint, Ward
from apps.warehouses.models import Branch

MFL = "99999"
NAME = "AfyaSync Synthetic Hospital"

DEPARTMENTS = [
    ("OPD", "Outpatient"),
    ("LAB", "Laboratory"),
    ("PHA", "Pharmacy"),
    ("IPD", "Inpatient"),
    ("FIN", "Finance"),
]
SERVICE_POINTS = [
    ("REC1", "Reception 1", ServicePoint.Kind.RECEPTION, "OPD"),
    ("TRI1", "Triage 1", ServicePoint.Kind.TRIAGE, "OPD"),
    ("CON1", "Consultation 1", ServicePoint.Kind.CONSULTATION, "OPD"),
    ("CON2", "Consultation 2", ServicePoint.Kind.CONSULTATION, "OPD"),
    ("ER", "Emergency", ServicePoint.Kind.EMERGENCY, "OPD"),
    ("LAB1", "Laboratory", ServicePoint.Kind.LAB, "LAB"),
    ("PHA1", "Pharmacy", ServicePoint.Kind.PHARMACY, "PHA"),
    ("CSH1", "Cashier 1", ServicePoint.Kind.CASHIER, "FIN"),
    ("REC", "Health records", ServicePoint.Kind.RECORDS, "OPD"),
]
WARDS = [
    ("FMW", "Female medical ward", Ward.Kind.GENERAL, Ward.Sex.FEMALE, 10),
    ("MMW", "Male medical ward", Ward.Kind.GENERAL, Ward.Sex.MALE, 10),
    ("PAE", "Paediatric ward", Ward.Kind.PAEDIATRIC, Ward.Sex.MIXED, 6),
]


def facility() -> Facility:
    return Facility.objects.get(mfl_code=MFL)


@transaction.atomic
def run(command: Any) -> None:
    branch, _ = Branch.objects.get_or_create(
        code="SYN",
        defaults={
            "name": NAME,
            "kra_pin": "P000000000A",
            "business_reg_no": "SYN-00001",
            "county": "NAIROBI",
            "physical_address": "Synthetic Road, Nairobi",
            "contact_phone": "+254700000000",
        },
    )
    site = Facility.objects.filter(mfl_code=MFL).first()
    if site is None:
        site = services.create_facility(
            branch=branch,
            actor=None,
            name=NAME,
            mfl_code=MFL,
            keph_level=Facility.KephLevel.LEVEL_4,
            odpc_controller_registration="ODPC-SYNTHETIC-0001",
        )
    departments = {}
    for code, name in DEPARTMENTS:
        departments[code] = Department.objects.filter(
            facility=site, code=code
        ).first() or services.create_department(facility=site, actor=None, code=code, name=name)
    for code, name, kind, department in SERVICE_POINTS:
        if not ServicePoint.objects.filter(facility=site, code=code).exists():
            services.create_service_point(
                facility=site,
                actor=None,
                code=code,
                name=name,
                kind=kind,
                department=departments[department],
            )
    for code, name, ward_kind, sex, beds in WARDS:
        ward = Ward.objects.filter(facility=site, code=code).first()
        if ward is None:
            ward = services.create_ward(
                facility=site,
                actor=None,
                code=code,
                name=name,
                kind=ward_kind,
                sex=sex,
                department=departments["IPD"],
            )
            for number in range(1, beds + 1):
                services.create_bed(ward=ward, actor=None, code=f"{code}-{number:02d}")
    command.stdout.write(f"  facility {site.name} (MFL {MFL}) with layout")
