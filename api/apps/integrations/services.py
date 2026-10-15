from .models import Notification, InventoryAlert
from .sms import SMSService
from .emails import EmailService
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
import secrets
from django.contrib.auth.hashers import make_password


def _get_user_model():
    return get_user_model()

class NotificationService:
    def __init__(self):
        self.sms_service = SMSService()
        self.email_service = EmailService()
        self.channel = getattr(settings, 'NOTIFICATION_CHANNEL', 'email').lower()

    def _preferred_notification_type(self):
        return 'sms' if self.channel == 'sms' else 'email'
    
    def send_notification(self, user, notification_type, subject, message):
        effective_type = notification_type
        if notification_type == 'sms' and self.channel != 'sms':
            effective_type = 'email'

        notification = Notification.objects.create(
            user=user,
            notification_type=effective_type,
            subject=subject,
            message=message,
        )
        
        if effective_type == 'sms':
            return self._send_sms_notification(user, message)
        elif effective_type == 'email':
            return self._send_email_notification(user, subject, message)
        
        notification.sent_at = timezone.now()
        notification.save()
        return True
    
    def _send_sms_notification(self, user, message):
        if not user.phone:
            return False
        result = self.sms_service.send_sms(user.phone, message)
        return result['success']
    
    def _send_email_notification(self, user, subject, message):
        if not user.email:
            return False
        return self.email_service.send_email(
            subject=subject,
            recipient=user.email,
            template_name="integrations/emails/generic_notification.html",
            context={'message': message}
        )
    
    def send_welcome_credentials(self, user, temp_password=None):
        if not temp_password:
            temp_password = secrets.token_urlsafe(8)
            user.password = make_password(temp_password)
            user.save()

        preferred = self._preferred_notification_type()

        if user.email:
            self.email_service.send_welcome_email(user, temp_password)

        if preferred == 'sms' and user.phone:
            sms_message = (
                f"{settings.SITE_NAME} credentials:\n"
                f"User: {user.email}\n"
                f"Pass: {temp_password}\n"
                f"Role: {user.get_role_display()}"
            )
            self._send_sms_notification(
                user=user,
                message=sms_message[:160]
            )

        return True
    
    def send_inventory_alert(self, product, alert_type, message):
        staff_users = _get_user_model().objects.filter(is_staff=True)
        for user in staff_users:
            self.send_notification(
                user=user,
                notification_type='email',
                subject=f"Inventory Alert: {alert_type} - {product.name}",
                message=message
            )
            InventoryAlert.objects.create(
                product=product,
                alert_type=alert_type,
                message=message
            )
    
    def send_staff_shift_notification(self, user, shift_details):
        subject = "Your Upcoming Work Shift"
        message = f"Shift details:\n{shift_details}"

        if self.channel == 'sms':
            self.send_notification(
                user=user,
                notification_type='sms',
                subject=subject,
                message=message,
            )

        self.send_notification(
            user=user,
            notification_type='email',
            subject=subject,
            message=message,
        )