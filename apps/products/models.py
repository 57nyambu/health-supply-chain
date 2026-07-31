from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import BaseModel
from django.utils.translation import gettext_lazy as _

class Category(BaseModel):
    """Simplified product categorization with Kenyan retail focus"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    vat_category = models.CharField(
        max_length=20,
        choices=[
            ('STANDARD', 'Standard Rate (16%)'),
            ('ZERO', 'Zero Rated (0%)'),
            ('EXEMPT', 'Exempt'),
        ],
        default='STANDARD'
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(BaseModel):
    """Optimized product model for Kenyan retail operations"""
    
    PRODUCT_TYPES = [
        ('PHYSICAL', 'Physical Product'),
        ('DIGITAL', 'Digital Product'),
        ('SERVICE', 'Service'),
    ]

    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50, blank=True)  # For receipts/display
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    sku = models.CharField(max_length=50, unique=True)  # Auto-generated if blank
    barcode = models.CharField(
        max_length=50, 
        blank=True, 
        unique=True,
        help_text="EAN-13, UPC, or custom barcode"
    )
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPES, default='PHYSICAL')
    buying_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    selling_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    wholesale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Bulk purchase price"
    )
    reorder_level = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    last_restocked = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['barcode']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def save(self, *args, **kwargs):
        if not self.sku:
            last_product = Product.objects.order_by('-id').first()
            last_id = last_product.id if last_product else 0
            self.sku = f"SKU-{self.created_at.year}-{last_id + 1:04d}"
        super().save(*args, **kwargs)

    @property
    def vat_amount(self):
        """Calculate VAT based on category"""
        if self.category.vat_category == 'STANDARD':
            return self.selling_price * 0.16
        return 0

class ProductImage(models.Model):
    """Essential product images with optimization"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to='products/%Y/%m/',
        help_text="Optimal size: 800x800px"
    )
    is_primary = models.BooleanField(default=False)
    caption = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-is_primary']

    def __str__(self):
        return f"Image for {self.product.name}"

class Inventory(BaseModel):
    """Streamlined inventory tracking"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey('warehouses.Warehouse', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    last_checked = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Inventory"
        unique_together = ('product', 'warehouse')
        indexes = [
            models.Index(fields=['product', 'warehouse']),
        ]

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse}: {self.quantity}"

    @property
    def needs_restock(self):
        return self.quantity <= self.product.reorder_level