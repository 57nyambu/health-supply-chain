"""Staff accounts API, behind default-deny policies and scoped to the active facility.

Users are never deleted (deactivation is a separate, audited action) and only users
linked to the request's facility — by a role assignment or a profile in its branch —
are visible. Sign-in lives in apps.accounts.api (/api/v1/auth/).
"""

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Q
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.access.drf import AUTHENTICATED, request_facility
from apps.accounts import login as auth
from apps.accounts.services import deactivate_user
from apps.audit.services import record
from apps.facilities.models import Facility

from .models import User, WorkerProfile
from .serializers import UserCreateSerializer, UserSerializer, WorkerProfileSerializer


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)


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
        "unlock": "admin.user.unlock",
        "deactivate": "admin.user.deactivate",
        "reset_credentials": "admin.user.reset_credentials",
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

    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        user = auth.unlock_account(
            self.get_object(), by=request.user, facility=request_facility(request)
        )
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=["post"], serializer_class=ReasonSerializer)
    def deactivate(self, request, pk=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = deactivate_user(
            self.get_object(),
            by=request.user,
            reason=serializer.validated_data["reason"],
            facility=request_facility(request),
        )
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=["post"], url_path="reset-credentials")
    def reset_credentials(self, request, pk=None):
        """Returns a one-time temporary password for the administrator to hand over in person."""
        temporary = auth.reset_credentials(
            self.get_object(), by=request.user, facility=request_facility(request)
        )
        return Response({"temporary_password": temporary, "must_change_password": True})


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
