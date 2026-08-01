from decimal import Decimal
from uuid import uuid4

from django.db import models

from apps.core.models import BaseModel


class Customer(BaseModel):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Order(BaseModel):
    STATUS_DRAFT = 'DRAFT'
    STATUS_PAID = 'PAID'
    STATUS_DELIVERED = 'DELIVERED'
    STATUS_CANCELLED = 'CANCELLED'

    PAYMENT_MPESA = 'MPESA'
    PAYMENT_CASH = 'CASH'
    PAYMENT_CARD = 'CARD'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PAID, 'Paid'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_MPESA, 'M-Pesa'),
        (PAYMENT_CASH, 'Cash'),
        (PAYMENT_CARD, 'Credit Card'),
    ]

    order_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True)
    warehouse = models.ForeignKey('warehouses.Warehouse', on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default=PAYMENT_CASH)
    mpesa_code = models.CharField(max_length=50, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def calculate_totals(self, save=True):
        gross_total = Decimal('0.00')
        tax_total = Decimal('0.00')

        for item in self.items.select_related('product').all():
            line_total = Decimal(item.quantity) * item.unit_price
            gross_total += line_total
            tax_total += line_total * (item.vat_rate / Decimal('100'))

        self.tax_amount = tax_total.quantize(Decimal('0.01'))
        self.total = (gross_total + self.tax_amount).quantize(Decimal('0.01'))

        if save:
            self.save(update_fields=['total', 'tax_amount', 'updated_at'])

        return self.total


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    vat_rate = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('16.00'))

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def line_total(self):
        return (Decimal(self.quantity) * self.unit_price).quantize(Decimal('0.01'))


class Receipt(BaseModel):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    receipt_number = models.CharField(max_length=50, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    sms_sent = models.BooleanField(default=False)
    sms_status = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['-issued_at']

    def __str__(self):
        return self.receipt_number

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"RCPT-{self.order.order_number}"
        super().save(*args, **kwargs)
from django.contrib.auth.models import AbstractUser, Group, Permission
