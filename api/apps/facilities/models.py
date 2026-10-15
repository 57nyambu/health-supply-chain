"""Facility registry data and the physical layout of a facility (DESIGN §4, §5, §6.3).

A Facility is one health facility (KMHFL MFL code) and is 1:1 with the legacy
``warehouses.Branch`` (ADR-018). Every PHI record is scoped to a facility.
"""

from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q

KRA_PIN = RegexValidator(r"^[A-Z]\d{9}[A-Z]$", "KRA PIN looks like A123456789B.")
MFL_CODE = RegexValidator(r"^\d{5,6}$", "MFL codes are 5 or 6 digits.")
FID = RegexValidator(r"^FID-[A-Za-z0-9-]+$", "Facility Registry IDs start with FID-.")


class Facility(models.Model):
    class KephLevel(models.IntegerChoices):
        LEVEL_2 = 2, "Level 2 — dispensary"
        LEVEL_3 = 3, "Level 3 — health centre"
        LEVEL_4 = 4, "Level 4 — sub-county hospital / medical centre"
        LEVEL_5 = 5, "Level 5 — county referral hospital"
        LEVEL_6 = 6, "Level 6 — national referral hospital"

    branch = models.OneToOneField(
        "warehouses.Branch", on_delete=models.PROTECT, related_name="facility"
    )
    name = models.CharField(max_length=150)
    mfl_code = models.CharField(
        "KMHFL MFL code", max_length=6, unique=True, null=True, blank=True, validators=[MFL_CODE]
    )
    fid = models.CharField(
        "Facility Registry ID", max_length=40, unique=True, null=True, blank=True, validators=[FID]
    )
    keph_level = models.PositiveSmallIntegerField(choices=KephLevel.choices, null=True, blank=True)
    sha_contract_number = models.CharField(max_length=50, blank=True)
    kra_pin = models.CharField("KRA PIN", max_length=11, blank=True, validators=[KRA_PIN])
    odpc_controller_registration = models.CharField(
        "ODPC registration (controller)", max_length=50, blank=True
    )
    odpc_processor_registration = models.CharField(
        "ODPC registration of the system vendor/host (processor)", max_length=50, blank=True
    )
    slade_provider_code = models.CharField(max_length=50, blank=True)
    mrn_format = models.CharField(
        max_length=60,
        default="{MFL}-{YY}-{seq:06d}",
        help_text="Placeholders: {MFL}, {YY}, {YYYY}, {seq} (gap-free per facility per year)",
    )
    # Security settings, bounded by DESIGN §7.2.
    require_mfa_for_all = models.BooleanField(default=False)
    workstation_lock_minutes = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(30)]
    )
    session_idle_minutes = models.PositiveSmallIntegerField(
        default=30, validators=[MinValueValidator(5), MaxValueValidator(120)]
    )
    session_absolute_hours = models.PositiveSmallIntegerField(
        default=12, validators=[MinValueValidator(1), MaxValueValidator(24)]
    )
    care_team_expiry_hours = models.PositiveSmallIntegerField(
        default=72, validators=[MinValueValidator(1), MaxValueValidator(720)]
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "facilities"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Department(models.Model):
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="departments")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["facility", "name"]
        constraints = [
            models.UniqueConstraint(fields=["facility", "code"], name="facilities_department_code"),
        ]

    def __str__(self) -> str:
        return self.name


class ServicePoint(models.Model):
    """A place with its own queue (DESIGN §6.3): triage, consultation room 1, cashier 2…"""

    class Kind(models.TextChoices):
        RECEPTION = "reception", "Reception"
        TRIAGE = "triage", "Triage"
        CONSULTATION = "consultation", "Consultation room"
        EMERGENCY = "emergency", "Emergency / resuscitation"
        LAB = "lab", "Laboratory"
        IMAGING = "imaging", "Imaging"
        PHARMACY = "pharmacy", "Pharmacy"
        CASHIER = "cashier", "Cashier"
        TREATMENT_ROOM = "treatment_room", "Treatment / procedure room"
        WARD_STATION = "ward_station", "Ward station"
        RECORDS = "records", "Health records"
        OTHER = "other", "Other"

    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="service_points")
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, null=True, blank=True, related_name="service_points"
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["facility", "kind", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "code"], name="facilities_servicepoint_code"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Ward(models.Model):
    class Kind(models.TextChoices):
        GENERAL = "general", "General"
        MATERNITY = "maternity", "Maternity"
        PAEDIATRIC = "paediatric", "Paediatric"
        NEWBORN = "newborn", "Newborn unit"
        ICU = "icu", "ICU"
        HDU = "hdu", "HDU"
        ISOLATION = "isolation", "Isolation"
        SURGICAL = "surgical", "Surgical"

    class Sex(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        MIXED = "mixed", "Mixed"

    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="wards")
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, null=True, blank=True, related_name="wards"
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.GENERAL)
    sex = models.CharField(max_length=10, choices=Sex.choices, default=Sex.MIXED)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["facility", "name"]
        constraints = [
            models.UniqueConstraint(fields=["facility", "code"], name="facilities_ward_code"),
        ]

    def __str__(self) -> str:
        return self.name


class Bed(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        OCCUPIED = "occupied", "Occupied"
        CLEANING = "cleaning", "Cleaning"
        OUT_OF_SERVICE = "out_of_service", "Out of service"

    ward = models.ForeignKey(Ward, on_delete=models.PROTECT, related_name="beds")
    code = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    active = models.BooleanField(default=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["ward", "code"]
        constraints = [
            models.UniqueConstraint(fields=["ward", "code"], name="facilities_bed_code"),
            models.CheckConstraint(
                condition=Q(active=True) | ~Q(status="occupied"),
                name="facilities_bed_inactive_not_occupied",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ward.code}-{self.code}"

    @property
    def facility_id(self) -> int:
        return self.ward.facility_id
