from django.db import models
from apps.core.models import BaseModel

class Customer(BaseModel):
    """Buyer details (retail/wholesale)."""
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, unique=True)  # For M-Pesa/SMS receipts
    email = models.EmailField(blank=True)
    tax_id = models.CharField(max_length=50, blank=True)  # KRA PIN for businesses
    address = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"

class Order(BaseModel):
    """Sales order (POS or wholesale)."""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PAID', 'Paid'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    PAYMENT_METHODS = [
        ('MPESA', 'M-Pesa'),
        ('CASH', 'Cash'),
        ('CARD', 'Credit Card'),
    ]
    order_number = models.CharField(max_length=50, unique=True)  # e.g., "ORD-2023-001"
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True)  # Walk-ins allowed
    warehouse = models.ForeignKey('warehouses.Warehouse', on_delete=models.PROTECT)  # Where stock is deducted
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='CASH')
    mpesa_code = models.CharField(max_length=50, blank=True)  # M-Pesa transaction ID
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Auto-calculated
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Kenyan VAT 16%

    def calculate_totals(self):
        """Update total + tax from order items."""
        items = self.items.all()
        subtotal = sum(item.total_price() for item in items)
        self.tax_amount = subtotal * 0.16  # Kenyan VAT
        self.total = subtotal + self.tax_amount
        self.save()

    def __str__(self):
        return f"Order #{self.order_number} ({self.get_status_display()})"

class OrderItem(models.Model):
    """Products sold in an order."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # Snapshot of price at sale time
    vat_rate = models.DecimalField(max_digits=4, decimal_places=2, default=16.0)

    def total_price(self):
        return self.quantity * self.unit_price * (1 + self.vat_rate / 100)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

class Receipt(BaseModel):
    """Generated invoice/SMS receipt for customers."""
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    receipt_number = models.CharField(max_length=50, unique=True)  # e.g., "RCPT-2023-001"
    issued_at = models.DateTimeField(auto_now_add=True)
    sms_sent = models.BooleanField(default=False)  # Track if SMS receipt was delivered (AfricasTalking)
    sms_status = models.CharField(max_length=50, blank=True)  # e.g., "Delivered", "Failed"

    def __str__(self):
        return f"Receipt #{self.receipt_number} for Order #{self.order.order_number}"