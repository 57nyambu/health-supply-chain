"""Service catalogue and price lists (DESIGN §10, P2-BIL-01).

A ``Service`` is anything the facility charges for. Prices live in effective-dated
``PriceListItem`` rows of a ``PriceList`` that is either the facility's cash list, a payer's
default list or a scheme's list; resolution is scheme → payer → cash. Price rows are never
edited in place: a change closes the current row and opens a new one, through maker-checker.
"""

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q

from apps.core.ids import uuid7


class Service(models.Model):
    class Kind(models.TextChoices):
        CONSULTATION = "consultation", "Consultation"
        LAB = "lab", "Laboratory test"
        IMAGING = "imaging", "Imaging"
        PROCEDURE = "procedure", "Procedure"
        BED_DAY = "bed_day", "Bed-day"
        NURSING = "nursing", "Nursing care"
        DRUG_DISPENSE = "drug_dispense", "Medicine dispensing"
        PACKAGE = "package", "Package"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING_APPROVAL = "pending_approval", "Waiting for approval"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    facility = models.ForeignKey(
        "facilities.Facility", on_delete=models.PROTECT, related_name="services"
    )
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=160)
    department = models.ForeignKey(
        "facilities.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="services",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    revenue_code = models.CharField(max_length=20, blank=True)
    # SHA intervention codes this service maps to (synthetic until Phase 3 imports the real
    # Benefits and Tariffs spreadsheet) and the KRA eTIMS item code (Phase 3 uses both).
    sha_interventions = ArrayField(models.CharField(max_length=40), default=list, blank=True)
    etims_item_code = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["facility", "kind", "name"]
        constraints = [
            models.UniqueConstraint(fields=["facility", "code"], name="billing_service_code"),
        ]

    def __str__(self) -> str:
        return f"{self.code} {self.name}"

    @property
    def active(self) -> bool:
        return self.status == self.Status.ACTIVE


class PriceList(models.Model):
    """Cash list (no payer, no scheme), a payer's default list, or a scheme's list."""

    class Basis(models.TextChoices):
        CASH = "cash", "Cash / self-pay"
        PAYER = "payer", "Payer default"
        SCHEME = "scheme", "Scheme"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    facility = models.ForeignKey(
        "facilities.Facility", on_delete=models.PROTECT, related_name="price_lists"
    )
    code = models.SlugField(max_length=40)
    name = models.CharField(max_length=120)
    payer = models.ForeignKey(
        "insurance.Payer", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    scheme = models.ForeignKey(
        "insurance.Scheme", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["facility", "name"]
        constraints = [
            models.UniqueConstraint(fields=["facility", "code"], name="billing_pricelist_code"),
            models.CheckConstraint(
                condition=Q(payer__isnull=True) | Q(scheme__isnull=True),
                name="billing_pricelist_payer_or_scheme",
            ),
            models.UniqueConstraint(
                fields=["facility"],
                condition=Q(payer__isnull=True, scheme__isnull=True, active=True),
                name="billing_one_active_cash_list",
            ),
            models.UniqueConstraint(
                fields=["facility", "payer"],
                condition=Q(payer__isnull=False, active=True),
                name="billing_one_active_list_per_payer",
            ),
            models.UniqueConstraint(
                fields=["facility", "scheme"],
                condition=Q(scheme__isnull=False, active=True),
                name="billing_one_active_list_per_scheme",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def basis(self) -> str:
        if self.scheme_id:
            return self.Basis.SCHEME
        if self.payer_id:
            return self.Basis.PAYER
        return self.Basis.CASH


class PriceListItem(models.Model):
    """One price of one service on one list for a date range (``effective_to`` inclusive)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    price_list = models.ForeignKey(PriceList, on_delete=models.PROTECT, related_name="items")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="prices")
    price = models.DecimalField(max_digits=14, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    approval = models.ForeignKey(
        "access.ApprovalRequest", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price_list", "service", "-effective_from"]
        indexes = [models.Index(fields=["price_list", "service", "effective_from"])]
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="billing_price_not_negative"),
            models.CheckConstraint(
                condition=Q(effective_to__isnull=True)
                | Q(effective_to__gte=models.F("effective_from")),
                name="billing_price_range_ordered",
            ),
            models.UniqueConstraint(
                fields=["price_list", "service"],
                condition=Q(effective_to__isnull=True),
                name="billing_one_open_price",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.service_id} @ {self.price} from {self.effective_from}"
