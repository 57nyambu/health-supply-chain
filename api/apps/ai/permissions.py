from django.conf import settings
from rest_framework.permissions import BasePermission

from apps.core.permissions import IsTier1 as CoreIsTier1
from apps.core.permissions import IsTier1OrTier2 as CoreIsTier1OrTier2


class IsTier1(CoreIsTier1):
    pass


class IsTier1OrTier2(CoreIsTier1OrTier2):
    pass


class HasPublicAPIKey(BasePermission):
    """Allows requests authenticated with the shared PUBLIC_API_KEY header."""

    def has_permission(self, request, view):
        key = request.headers.get('X-API-Key')
        expected = getattr(settings, 'PUBLIC_API_KEY', '')
        return bool(expected and key and key == expected)
