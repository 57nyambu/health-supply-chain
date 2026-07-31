from celery import shared_task
from django.utils import timezone
from .models import SalesReport
from sales.models import Order
from datetime import timedelta
from apps.integrations.sms import SMSService

@shared_task
def generate_daily_sales_report():
    """Auto-generate daily sales reports at midnight EAT."""
    today = timezone.now().date()
    orders = Order.objects.filter(
        created_at__date=today,
        status='PAID'
    )
    
    SalesReport.objects.create(
        period_type='DAILY',
        start_date=today,
        end_date=today,
        total_sales=sum(order.total for order in orders),
        total_orders=orders.count(),
        mpesa_payments=orders.filter(payment_method='MPESA').count()
    )

@shared_task
def send_daily_executive_summary():
    report = SalesReport.objects.latest('created_at')
    message = (
        f"Daily Report: KES {report.total_sales} "
        f"from {report.total_orders} orders. "
        f"M-Pesa: {report.mpesa_payments} payments."
    )
    SMSService().send_receipt("2547XXXXXXX", message)  # CEO's number