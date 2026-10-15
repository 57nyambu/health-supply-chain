from celery import shared_task
from .services import NotificationService
from .models import Notification, InventoryAlert
from django.utils import timezone
from apps.products.models import Product
from django.conf import settings

@shared_task(bind=True, max_retries=3)
def send_notification_task(self, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id)
        service = NotificationService()
        
        if notification.notification_type == 'sms':
            service._send_sms_notification(notification.user, notification.message)
        elif notification.notification_type == 'email':
            service._send_email_notification(
                notification.user,
                notification.subject,
                notification.message
            )
        
        notification.sent_at = timezone.now()
        notification.save()
        return True
    except Exception as e:
        self.retry(exc=e, countdown=60)

@shared_task(bind=True, max_retries=3)
def send_welcome_credentials_task(self, user_id, temp_password=None):
    try:
        from apps.accounts.models import User
        user = User.objects.get(id=user_id)
        service = NotificationService()
        return service.send_welcome_credentials(user, temp_password)
    except Exception as e:
        self.retry(exc=e, countdown=60)

@shared_task(bind=True, max_retries=3)
def check_low_stock_items(self):
    try:
        low_stock_threshold = getattr(settings, 'LOW_STOCK_THRESHOLD', 10)
        low_stock_items = Product.objects.filter(
            quantity__lte=low_stock_threshold,
            is_active=True
        )
        
        notification_service = NotificationService()
        
        for product in low_stock_items:
            message = f"Product {product.name} is running low. Current stock: {product.quantity}"
            notification_service.send_inventory_alert(
                product=product,
                alert_type='low_stock',
                message=message
            )
            
        return f"Checked {low_stock_items.count()} low stock items"
    except Exception as e:
        self.retry(exc=e, countdown=60)