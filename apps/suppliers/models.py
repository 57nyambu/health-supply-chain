from django.db import models
from apps.core.models import BaseModel

class Supplier(BaseModel):
    """Vendor/Supplier details (local Kenyan businesses)."""
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)  # M-Pesa contact (e.g., "+254712345678")
    email = models.EmailField(blank=True)
    address = models.TextField()
    tax_id = models.CharField(max_length=50, blank=True)  # Kenyan KRA PIN
    payment_terms = models.CharField(max_length=100, default="30 days")  # e.g., "Cash on Delivery"

    def __str__(self):
        return self.name

class PurchaseOrder(BaseModel):
    """Order placed with a supplier."""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent to Supplier'),
        ('PARTIAL', 'Partially Fulfilled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    po_number = models.CharField(max_length=50, unique=True)  # e.g., "PO-2023-001"
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    order_date = models.DateField()
    delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.po_number} - {self.supplier.name}"

class PurchaseOrderItem(models.Model):
    """Line items in a purchase order."""
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # In KES
    vat_rate = models.DecimalField(max_digits=4, decimal_places=2, default=16.0)  # Kenyan VAT

    def total_price(self):
        return self.quantity * self.unit_price * (1 + self.vat_rate / 100)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

class SupplierPayment(BaseModel):
    """Record M-Pesa/bank payments to suppliers."""
    PAYMENT_METHODS = [
        ('MPESA', 'M-Pesa'),
        ('BANK', 'Bank Transfer'),
        ('CASH', 'Cash'),
    ]
    order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='MPESA')
    transaction_id = models.CharField(max_length=100, blank=True)  # M-Pesa transaction ID
    payment_date = models.DateTimeField(auto_now_add=True)
    confirmed = models.BooleanField(default=False)  # Verified by accounting

    def __str__(self):
        return f"Payment of KES {self.amount} to {self.order.supplier.name}"