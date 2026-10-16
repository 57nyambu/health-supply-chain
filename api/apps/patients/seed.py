"""Seed step: synthetic patients (IMPLEMENTATION §8) — curated Kenyan-plausible name lists,
combined at random, never real people. National IDs start with 000; phones use the Daraja
sandbox test number. Registered through the normal service (encrypted, audited)."""

import random
from datetime import date, timedelta
from typing import Any

from apps.accounts.models import User
from apps.accounts.seed import email_for
from apps.facilities import seed as facility_seed
from apps.patients import privacy, services
from apps.patients.models import Patient

COUNT = 500
SANDBOX_PHONE = "+254708374149"
FEMALE = [
    "Achieng",
    "Wanjiru",
    "Njeri",
    "Akinyi",
    "Chebet",
    "Wambui",
    "Nafula",
    "Atieno",
    "Mwende",
    "Halima",
    "Zawadi",
    "Nekesa",
    "Jepkosgei",
    "Kerubo",
    "Makena",
    "Auma",
    "Fatuma",
    "Moraa",
    "Nyokabi",
    "Imani",
]
MALE = [
    "Otieno",
    "Kamau",
    "Kiprono",
    "Mwangi",
    "Omondi",
    "Mutua",
    "Wafula",
    "Kipchoge",
    "Hassan",
    "Njoroge",
    "Barasa",
    "Onyango",
    "Kibet",
    "Muriuki",
    "Ochieng",
    "Juma",
    "Kariuki",
    "Nyamweya",
    "Wekesa",
    "Baraka",
]
FAMILY = [
    "Odhiambo",
    "Kamau",
    "Wanjiku",
    "Ochieng",
    "Mutua",
    "Kiptoo",
    "Njoroge",
    "Wafula",
    "Omondi",
    "Muthoni",
    "Kariuki",
    "Achieng",
    "Kiprotich",
    "Mohamed",
    "Nyaga",
    "Owino",
    "Cheruiyot",
    "Mwangi",
    "Okoth",
    "Wairimu",
]


def run(command: Any) -> None:
    site = facility_seed.facility()
    existing = Patient.objects.filter(facility=site).count()
    if existing >= COUNT:
        command.stdout.write(f"  patients: {existing} already present")
        return
    actor = User.objects.get(email=email_for("hrio"))
    rng = random.Random(20261016)  # noqa: S311 - deterministic synthetic data, not security
    for n in range(existing, COUNT):
        sex = "female" if n % 2 == 0 else "male"
        given = rng.choice(FEMALE if sex == "female" else MALE)
        dob = date(1940, 1, 1) + timedelta(days=rng.randrange(0, 365 * 85))
        services.create_patient(
            facility=site,
            actor=actor,
            given_name=given,
            family_name=rng.choice(FAMILY),
            sex=sex,
            date_of_birth=dob,
            identifiers=[{"type": "national_id", "value": f"000{n:05d}"}]
            if dob.year < 2008
            else [],
            contacts=[{"kind": "phone", "value": SANDBOX_PHONE, "is_primary": True}]
            if n % 5 == 0
            else [],
            override_reason="Synthetic seed data",
            privacy_notice={"version": privacy.NOTICE_VERSION, "method": "verbal"},
        )
    command.stdout.write(f"  patients: {COUNT - existing} synthetic patients registered")
