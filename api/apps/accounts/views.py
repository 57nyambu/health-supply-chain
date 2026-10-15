"""Staff accounts API, behind default-deny policies and scoped to the active facility.

Users are never deleted (deactivation is a separate, audited action) and only users
linked to the request's facility — by a role assignment or a profile in its branch —
are visible. The legacy login keeps its response shape until P1-UAC-04 replaces it.
"""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Q
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.access.drf import AUTHENTICATED, PUBLIC, request_facility
from apps.accounts.legacy import legacy_tier, legacy_warehouse_id
from apps.audit.services import record
from apps.facilities.models import Facility

from .models import User, WorkerProfile
from .serializers import (
    AuthSerializer,
    UserCreateSerializer,
    UserSerializer,
    WorkerProfileSerializer,
)


def _facility_users(facility_id: int | None):
    if facility_id is None:
        return User.objects.none()
    return (
        User.objects.filter(
            Q(role_assignments__facility_id=facility_id)
            | Q(profile__branch__facility__id=facility_id)
        )
        .distinct()
        .order_by("email")
    )


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = UserSerializer
    queryset = User.objects.none()
    policy = {
        "list": "admin.user.read",
        "retrieve": "admin.user.read",
        "create": "admin.user.create",
        "update": "admin.user.update",
        "partial_update": "admin.user.update",
        "me": AUTHENTICATED,
    }

    def get_queryset(self):
        return _facility_users(request_facility(self.request))

    def facility_of(self, obj):
        return request_facility(self.request)  # the queryset is already facility-scoped

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return super().get_serializer_class()

    @transaction.atomic
    def perform_create(self, serializer):
        password = serializer.validated_data.get("password")
        try:
            validate_password(password)
        except Exception as exc:  # Django ValidationError → field error
            raise serializers.ValidationError(
                {"password": list(getattr(exc, "messages", []))}
            ) from exc
        user = serializer.save()
        facility = Facility.objects.get(pk=request_facility(self.request))
        WorkerProfile.objects.get_or_create(user=user, defaults={"branch": facility.branch})
        record("admin.user.created", self.request.user, user, facility=facility)

    @transaction.atomic
    def perform_update(self, serializer):
        changed = sorted(
            field
            for field, value in serializer.validated_data.items()
            if getattr(serializer.instance, field) != value
        )
        user = serializer.save()
        if changed:
            record(
                "admin.user.updated",
                self.request.user,
                user,
                facility=request_facility(self.request),
                detail={"fields": changed},
            )

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(UserSerializer(request.user).data)


class WorkerProfileViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = WorkerProfileSerializer
    queryset = WorkerProfile.objects.none()
    policy = {
        "list": "admin.user.read",
        "retrieve": "admin.user.read",
        "update": "admin.user.update",
        "partial_update": "admin.user.update",
    }

    def get_queryset(self):
        facility_id = request_facility(self.request)
        if facility_id is None:
            return WorkerProfile.objects.none()
        return WorkerProfile.objects.filter(branch__facility__id=facility_id).select_related("user")

    def facility_of(self, obj):
        return request_facility(self.request)

    def perform_update(self, serializer):
        profile = serializer.save()
        record(
            "admin.user.profile_updated",
            self.request.user,
            profile,
            facility=request_facility(self.request),
            detail={"fields": sorted(serializer.validated_data)},
        )


class AuthViewSet(viewsets.ViewSet):
    """Legacy login/logout (session + JWT). Replaced by the P1-UAC-04 auth API."""

    serializer_class = AuthSerializer
    policy = {"login": PUBLIC, "logout": PUBLIC}

    @action(detail=False, methods=["post"])
    def login(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            record("auth.login.failed", None, outcome="denied")
            return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        record("auth.login.succeeded", user, user)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "status": "logged in",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role,
                    "role_display": user.get_role_display(),
                    "tier": legacy_tier(user),
                    "warehouse_id": legacy_warehouse_id(user),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
            }
        )

    @action(detail=False, methods=["post"])
    def logout(self, request):
        if request.user.is_authenticated:
            record("auth.logout", request.user, request.user)
        logout(request)
        return Response({"status": "logged out"})
