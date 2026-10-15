import africastalking
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from apps.core.models import AuditLog

class SMSService:
    """Send SMS receipts via AfricasTalking API."""
    def __init__(self):
        self.username = getattr(settings, 'AT_USERNAME', 'sandbox')
        self.api_key = getattr(settings, 'AT_API_KEY', '')
        if not self.api_key:
            raise ImproperlyConfigured("AfricasTalking API key missing in settings.")
        africastalking.initialize(self.username, self.api_key)
        self.sms = africastalking.SMS

    def send_receipt(self, phone, message):
        """Send SMS receipt to customer."""
        try:
            response = self.sms.send(message, [phone])
            AuditLog.objects.create(
                action="CREATE",
                model="SMSReceipt",
                details={"phone": phone, "status": response['SMSMessageData']['Recipients'][0]['status']}
            )
            return response
        except Exception as e:
            AuditLog.objects.create(
                action="ERROR",
                model="SMSReceipt",
                details={"error": str(e)}
            )
            raise
            
class SMSService2:  
    def send_receipt(self, phone, order):  
        """Send formatted SMS receipt."""  
        message = (  
            f"Receipt #{order.receipt.receipt_number}\n"  
            f"Date: {order.receipt.issued_at.strftime('%d/%m/%Y %H:%M')}\n"  
            f"Items: {order.items.count()}\n"  
            f"Total: KES {order.total}\n"  
            f"Thank you!"  
        )  
        try:  
            response = self.sms.send(message, [phone], sender_id=settings.AT_SENDER_ID)  
            return response['SMSMessageData']['Recipients'][0]['status'] == 'Success'  
        except Exception as e:  
            raise Exception(f"SMS failed: {str(e)}")  