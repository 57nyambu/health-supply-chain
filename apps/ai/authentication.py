from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class PublicAPIKeyAuth(BaseAuthentication):
    """Simple API-key authentication for read-only external public endpoints."""

    def authenticate(self, request):
        key = request.headers.get('X-API-Key')
        if not key:
            return None

        expected = getattr(settings, 'PUBLIC_API_KEY', '')
        if not expected or key != expected:
            raise AuthenticationFailed('Invalid API key')

        # No internal user object is attached for external consumers.
        return (None, key)
