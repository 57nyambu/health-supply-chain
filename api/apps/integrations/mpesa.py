import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from apps.core.models import AuditLog
from apps.sales.models import Order, Receipt
from datetime import datetime
import base64

class MpesaGateway:
    """Handle M-Pesa STK Push and callbacks."""
    def __init__(self):
        self.consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        self.business_shortcode = getattr(settings, 'MPESA_BUSINESS_SHORTCODE', '')
        self.passkey = getattr(settings, 'MPESA_PASSKEY', '')
        self.callback_url = getattr(settings, 'MPESA_CALLBACK_URL', '')
        self.auth_token = None

    def _get_auth_token(self):
        """Get OAuth token from Safaricom API."""
        url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        response = requests.get(
            url,
            auth=(self.consumer_key, self.consumer_secret),
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            self.auth_token = response.json().get('access_token')
            return self.auth_token
        raise ImproperlyConfigured("Failed to authenticate M-Pesa API.")

    def stk_push(self, phone, amount, order_id, description):
        """Initiate STK Push payment request."""
        if not self.auth_token:
            self._get_auth_token()

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f"{self.business_shortcode}{self.passkey}{timestamp}".encode()
        ).decode()

        payload = {
            "BusinessShortCode": self.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,  # Customer's phone
            "PartyB": self.business_shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self.callback_url,
            "AccountReference": f"ORDER_{order_id}",
            "TransactionDesc": description
        }

        headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json'
        }

        response = requests.post(
            'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest',
            json=payload,
            headers=headers
        )

        if response.status_code == 200:
            AuditLog.objects.create(
                action="CREATE",
                model="MpesaPayment",
                object_id=order_id,
                details={"status": "initiated", "amount": amount}
            )
            return response.json()
        raise Exception(f"M-Pesa STK Push failed: {response.text}")

    def handle_callback(self, data):
        """Process M-Pesa payment confirmation callback."""
        # Save payment status to Order model
        order_id = data['AccountReference'].split('_')[1]
        order = Order.objects.get(id=order_id)
        order.mpesa_code = data['MpesaReceiptNumber']
        order.status = 'PAID'
        order.save()

        # Generate receipt
        Receipt.objects.create(
            order=order,
            receipt_number=f"RCPT-{order.order_number}",
            sms_sent=False  # Will trigger SMS via signals
        )