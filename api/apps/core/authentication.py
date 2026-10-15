"""
Tier 3 (external) authentication — for third-party integrators consuming the
open, read-only /api/v1/public/ namespace. No user account is created or
required; a single shared key is enough for the hackathon demo (see
FRONTEND_AND_API_SPEC.md for the production upgrade path: a PublicAPIKey
model with per-integrator keys).
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings


class PublicAPIKeyAuthentication(BaseAuthentication):
    """Expects header: X-API-Key: <PUBLIC_API_KEY>"""

    def authenticate(self, request):
        key = request.headers.get('X-API-Key')
        if not key:
            return None  # let other authenticators run / view can require auth
        if not getattr(settings, 'PUBLIC_API_KEY', None) or key != settings.PUBLIC_API_KEY:
            raise AuthenticationFailed('Invalid API key.')
        return (None, None)  # no user object; request.user stays AnonymousUser


class IsValidPublicAPIKey:
    """Simple permission companion — use alongside PublicAPIKeyAuthentication."""
    def has_permission(self, request, view):
        key = request.headers.get('X-API-Key')
        return bool(key) and key == getattr(settings, 'PUBLIC_API_KEY', None)