from django.db import models
from apps.core.models import BaseModel

class SalesReport(BaseModel):
    """Aggregated sales data (daily/weekly/monthly)."""
    REPORT_PERIODS = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    ]
    period_type = models.CharField(max_length=10, choices=REPORT_PERIODS)
    start_date = models.DateField()
    end_date = models.DateField()
    total_sales = models.DecimalField(max_digits=12, decimal_places=2)  # KES
    total_orders = models.PositiveIntegerField()
    top_product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True)
    mpesa_payments = models.PositiveIntegerField()  # Track M-Pesa adoption

    class Meta:
        indexes = [
            models.Index(fields=['start_date', 'period_type']),
        ]


class RTInventoryAlert(BaseModel):
    """Real-time low stock alerts."""
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    current_stock = models.PositiveIntegerField()
    warehouse = models.ForeignKey('warehouses.Warehouse', on_delete=models.CASCADE)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Low stock: {self.product.name} ({self.current_stock})"