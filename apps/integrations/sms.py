import africastalking
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import logging

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self):
        if not all([settings.AFRICASTALKING_USERNAME, settings.AFRICASTALKING_API_KEY]):
            raise ImproperlyConfigured("Africa's Talking credentials not configured")
            
        africastalking.initialize(
            username=settings.AFRICASTALKING_USERNAME,
            api_key=settings.AFRICASTALKING_API_KEY
        )
        self.sms = africastalking.SMS
    
    def send_sms(self, phone_number, message):
        try:
            response = self.sms.send(message, [phone_number])
            return {
                'success': True,
                'response': response,
                'recipient': phone_number
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'recipient': phone_number
            }
    
    def send_generic_sms(self, phone_number, context):
        try:
            if context.get('template') == 'welcome_credentials':
                sms_msg = (
                    f"{context.get('site_name', 'Work')} Credentials:\n"
                    f"User: {context['username']}\n"
                    f"Pass: {context['password']}\n"
                    f"Role: {context.get('role', 'Worker')}"
                )
            else:
                sms_msg = f"{context.get('subject', 'Notification')}: {context['message']}"
            
            sms_msg = sms_msg[:160]
            return self.send_sms(phone_number, sms_msg)
        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }