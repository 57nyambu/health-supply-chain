from django.db import models
from django.core.validators import RegexValidator
from apps.core.models import BaseModel
from .choices import (
    COUNTY_CHOICES,
    WAREHOUSE_TYPES,
    BIN_TYPES,
    STOCK_TRANSFER_STATUS_CHOICES,
    STOCK_TRANSFER_TYPES,
)

class Branch(BaseModel):
    """Enhanced business branch model with Kenyan compliance"""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)  # e.g., "NRB", "MSA"
    kra_pin = models.CharField(
        max_length=11,
        validators=[RegexValidator(r'^[A-Z]{1}\d{9}[A-Z]{1}$')],
        verbose_name="KRA PIN"
    )
    business_reg_no = models.CharField(max_length=20, verbose_name="Business Registration Number")
    vat_no = models.CharField(max_length=20, blank=True, verbose_name="VAT Number")
    county = models.CharField(max_length=50, choices=COUNTY_CHOICES)
    physical_address = models.TextField()
    postal_address = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+254\d{9}$')]
    )
    contact_email = models.EmailField(blank=True)
    manager = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role__in': ['ADMIN', 'BRANCH_MANAGER']}
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Branches"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

class Warehouse(BaseModel):
    """Physical storage location with enhanced tracking"""

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)  # e.g., "WH-NRB-01"
    warehouse_type = models.CharField(max_length=10, choices=WAREHOUSE_TYPES, default='DRY')
    physical_address = models.TextField()
    contact_phone = models.CharField(max_length=15)  # +254...
    manager = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role__in': ['WAREHOUSE', 'BRANCH_MANAGER']}
    )
    capacity = models.PositiveIntegerField(help_text="Total capacity in cubic meters", null=True, blank=True)
    temperature_controlled = models.BooleanField(default=False)
    temperature_range = models.CharField(max_length=20, blank=True)  # e.g., "2-8°C"

    class Meta:
        ordering = ['branch', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})"

class BinLocation(BaseModel):
    """Enhanced shelf/bin tracking with barcode support"""

    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)  # e.g., "Aisle 3, Shelf B"
    bin_type = models.CharField(max_length=10, choices=BIN_TYPES, default='SHELF')
    barcode = models.CharField(max_length=50, blank=True, unique=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    capacity = models.PositiveIntegerField(help_text="Max items that can be stored", null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('warehouse', 'name')
        verbose_name = "Bin Location"

    def __str__(self):
        return f"{self.name} @ {self.warehouse.name}"

class StockTransfer(BaseModel):
    """Enhanced stock movement tracking with Kenyan compliance"""

    reference_no = models.CharField(max_length=20, unique=True)  # e.g., "TRF-2023-001"
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    transfer_type = models.CharField(max_length=10, choices=STOCK_TRANSFER_TYPES, default='INTERNAL')
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='transfers_out')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='transfers_in')
    from_bin = models.ForeignKey(BinLocation, on_delete=models.PROTECT, related_name='transfers_out', null=True, blank=True)
    to_bin = models.ForeignKey(BinLocation, on_delete=models.PROTECT, related_name='transfers_in', null=True, blank=True)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=15, choices=STOCK_TRANSFER_STATUS_CHOICES, default='PENDING')
    initiated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='initiated_transfers'
    )
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='approved_transfers',
        null=True,
        blank=True
    )
    delivery_note = models.CharField(max_length=50, blank=True)
    transporter = models.CharField(max_length=100, blank=True)
    transporter_license = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Stock Transfer"

    def __str__(self):
        return f"{self.reference_no}: {self.product.name} ({self.quantity})"

    def save(self, *args, **kwargs):
        if not self.reference_no:
            last_transfer = StockTransfer.objects.order_by('-id').first()
            last_id = last_transfer.id if last_transfer else 0
            self.reference_no = f"TRF-{self.created_at.year}-{last_id + 1:04d}"
        super().save(*args, **kwargs)