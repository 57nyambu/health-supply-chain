"""Seed step: service catalogue and price lists of the synthetic facility (GUIDE-PHASE-2).

Prices are synthetic KES amounts. SHA intervention codes are **synthetic placeholders**
(``SYN-SHA-…``) until Phase 3 imports the real SHA Benefits and Tariffs spreadsheet — never
treat them as tariffs (PHASE-2 pitfalls). Seeding skips maker-checker (bootstrap only,
refused in production by the seed command).
"""

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.billing import services
from apps.billing.models import PriceList, PriceListItem, Service
from apps.facilities import seed as facility_seed
from apps.facilities.models import Department
from apps.insurance.models import Payer, Scheme

K = Service.Kind
# code, name, kind, department, cash price, SHA (SHIF) price or None, synthetic interventions
CATALOGUE: list[tuple[str, str, str, str, str, str | None, list[str]]] = [
    (
        "CONS-GEN",
        "General outpatient consultation",
        K.CONSULTATION,
        "OPD",
        "500.00",
        "500.00",
        ["SYN-SHA-OPD-001"],
    ),
    (
        "CONS-FU",
        "Follow-up consultation",
        K.CONSULTATION,
        "OPD",
        "300.00",
        "300.00",
        ["SYN-SHA-OPD-002"],
    ),
    (
        "CONS-SPEC",
        "Specialist consultation",
        K.CONSULTATION,
        "OPD",
        "1500.00",
        "1200.00",
        ["SYN-SHA-OPD-003"],
    ),
    (
        "CONS-EMER",
        "Emergency consultation",
        K.CONSULTATION,
        "OPD",
        "1000.00",
        "1000.00",
        ["SYN-SHA-EMR-001"],
    ),
    ("LAB-FBC", "Full blood count", K.LAB, "LAB", "800.00", "600.00", ["SYN-SHA-LAB-001"]),
    (
        "LAB-BSMPS",
        "Malaria blood slide (BS for MPs)",
        K.LAB,
        "LAB",
        "300.00",
        "250.00",
        ["SYN-SHA-LAB-002"],
    ),
    (
        "LAB-MRDT",
        "Malaria rapid diagnostic test",
        K.LAB,
        "LAB",
        "250.00",
        "200.00",
        ["SYN-SHA-LAB-003"],
    ),
    ("LAB-RBS", "Random blood sugar", K.LAB, "LAB", "200.00", "150.00", ["SYN-SHA-LAB-004"]),
    ("LAB-HB", "Haemoglobin", K.LAB, "LAB", "200.00", "150.00", ["SYN-SHA-LAB-005"]),
    ("LAB-UA", "Urinalysis", K.LAB, "LAB", "300.00", "250.00", ["SYN-SHA-LAB-006"]),
    ("LAB-K", "Serum potassium", K.LAB, "LAB", "600.00", "500.00", ["SYN-SHA-LAB-007"]),
    ("LAB-WIDAL", "Widal test", K.LAB, "LAB", "400.00", None, []),
    ("LAB-HIV", "HIV rapid test", K.LAB, "LAB", "0.00", "0.00", ["SYN-SHA-LAB-008"]),
    ("IMG-CXR", "Chest X-ray", K.IMAGING, "OPD", "1500.00", "1200.00", ["SYN-SHA-IMG-001"]),
    ("IMG-XRLIMB", "Limb X-ray", K.IMAGING, "OPD", "1200.00", "1000.00", ["SYN-SHA-IMG-002"]),
    (
        "IMG-USSABD",
        "Abdominal ultrasound",
        K.IMAGING,
        "OPD",
        "2500.00",
        "2000.00",
        ["SYN-SHA-IMG-003"],
    ),
    (
        "IMG-USSOBS",
        "Obstetric ultrasound",
        K.IMAGING,
        "OPD",
        "2000.00",
        "1800.00",
        ["SYN-SHA-IMG-004"],
    ),
    ("PRC-DRESS", "Wound dressing", K.PROCEDURE, "OPD", "300.00", "300.00", ["SYN-SHA-PRC-001"]),
    ("PRC-SUTURE", "Wound suturing", K.PROCEDURE, "OPD", "1000.00", "800.00", ["SYN-SHA-PRC-002"]),
    ("PRC-IVCAN", "IV cannulation", K.PROCEDURE, "OPD", "200.00", "200.00", ["SYN-SHA-PRC-003"]),
    (
        "PRC-INJ",
        "Injection administration",
        K.PROCEDURE,
        "OPD",
        "100.00",
        "100.00",
        ["SYN-SHA-PRC-004"],
    ),
    ("PRC-NEB", "Nebulisation", K.PROCEDURE, "OPD", "300.00", "300.00", ["SYN-SHA-PRC-005"]),
    (
        "PRC-CATH",
        "Urinary catheterisation",
        K.PROCEDURE,
        "IPD",
        "500.00",
        "500.00",
        ["SYN-SHA-PRC-006"],
    ),
    (
        "BED-GEN",
        "General ward bed-day",
        K.BED_DAY,
        "IPD",
        "2000.00",
        "2240.00",
        ["SYN-SHA-IPD-001"],
    ),
    (
        "BED-PAE",
        "Paediatric ward bed-day",
        K.BED_DAY,
        "IPD",
        "1500.00",
        "2240.00",
        ["SYN-SHA-IPD-002"],
    ),
    ("NURS-DAY", "Inpatient nursing care (per day)", K.NURSING, "IPD", "800.00", None, []),
    ("DISP-FEE", "Dispensing fee", K.DRUG_DISPENSE, "PHA", "50.00", "0.00", []),
]
INSURER_A_DISCOUNT = Decimal("0.90")  # synthetic: insurer A pays 90 % of cash prices


def _lists(site: Any) -> dict[str, PriceList]:
    sha_shif = Scheme.objects.get(payer__code="sha", code="shif")
    insurer_a = Payer.objects.get(code="syn-insurer-a")
    wanted = [
        ("cash", "Cash prices", None, None),
        ("sha-shif", "SHA — SHIF (synthetic prices)", None, sha_shif),
        ("syn-insurer-a", "Synthetic Insurer A (default)", insurer_a, None),
    ]
    lists = {}
    for code, name, payer, scheme in wanted:
        lists[code] = PriceList.objects.filter(facility=site, code=code).first() or (
            services.create_price_list(
                facility=site, actor=None, code=code, name=name, payer=payer, scheme=scheme
            )
        )
    return lists


def _price(price_list: PriceList, service: Service, amount: str, start: Any) -> None:
    if not PriceListItem.objects.filter(price_list=price_list, service=service).exists():
        services._set_price(
            price_list=price_list,
            service=service,
            price=Decimal(amount),
            effective_from=start,
            actor=None,
        )


@transaction.atomic
def run(command: Any) -> None:
    site = facility_seed.facility()
    departments = {d.code: d for d in Department.objects.filter(facility=site)}
    lists = _lists(site)
    start = timezone.localdate().replace(day=1).replace(year=timezone.localdate().year - 1)
    for code, name, kind, dept, cash, sha, interventions in CATALOGUE:
        service = Service.objects.filter(
            facility=site, code=code
        ).first() or services._create_service(
            facility=site,
            actor=None,
            code=code,
            name=name,
            kind=kind,
            department=departments.get(dept),
            sha_interventions=interventions,
            revenue_code=f"REV-{kind.upper()[:6]}",
        )
        _price(lists["cash"], service, cash, start)
        if sha is not None:
            _price(lists["sha-shif"], service, sha, start)
        _price(
            lists["syn-insurer-a"],
            service,
            str((Decimal(cash) * INSURER_A_DISCOUNT).quantize(Decimal("0.01"))),
            start,
        )
    command.stdout.write(f"  billing: {len(CATALOGUE)} services, {len(lists)} price lists")
