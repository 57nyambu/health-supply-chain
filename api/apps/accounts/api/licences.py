"""Professional licences API (P1-UAC-07), scoped to staff of the request's facility."""

from typing import Any

from django.db.models import Q, QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.access.drf import request_facility
from apps.accounts import licences
from apps.accounts.models import ProfessionalLicence, User


def _facility_user_ids(facility_id: int | None) -> QuerySet[User]:
    return User.objects.filter(
        Q(role_assignments__facility_id=facility_id) | Q(profile__branch__facility__id=facility_id)
    ).distinct()


class LicenceSerializer(serializers.ModelSerializer[ProfessionalLicence]):
    class Meta:
        model = ProfessionalLicence
        fields = [
            "id",
            "user",
            "regulator",
            "registration_number",
            "licence_number",
            "valid_from",
            "valid_to",
            "puid",
            "slade_code",
            "verified_at",
            "verification_source",
            "active",
        ]
        read_only_fields = ["id", "puid", "verified_at", "verification_source"]


class LicenceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet[ProfessionalLicence],
):
    serializer_class = LicenceSerializer
    queryset = ProfessionalLicence.objects.none()
    http_method_names = ["get", "post", "patch"]
    policy = {
        "list": "access.licence.read",
        "retrieve": "access.licence.read",
        "create": "access.licence.manage",
        "partial_update": "access.licence.manage",
        "verify": "access.licence.manage",
    }

    def get_queryset(self) -> QuerySet[ProfessionalLicence]:
        facility_id = request_facility(self.request)
        queryset = ProfessionalLicence.objects.filter(user__in=_facility_user_ids(facility_id))
        user = self.request.query_params.get("user")
        return queryset.filter(user_id=user) if user else queryset

    def facility_of(self, obj: ProfessionalLicence) -> int | None:
        return request_facility(self.request)

    def perform_create(self, serializer: Any) -> None:
        data = dict(serializer.validated_data)
        user = data.pop("user")
        facility_id = request_facility(self.request)
        if not _facility_user_ids(facility_id).filter(pk=user.pk).exists():
            raise serializers.ValidationError(
                {"user": "Choose a member of staff of your facility."}
            )
        serializer.instance = licences.add_licence(
            user=user, actor=self.request.user, facility=facility_id, **data
        )

    def perform_update(self, serializer: Any) -> None:
        data = dict(serializer.validated_data)
        data.pop("user", None)
        serializer.instance = licences.update_licence(
            self.get_object(),
            actor=self.request.user,
            facility=request_facility(self.request),
            **data,
        )

    @extend_schema(request=None)
    @action(detail=True, methods=["post"])
    def verify(self, request: Request, pk: str | None = None) -> Response:
        licence = licences.verify_licence(
            self.get_object(), actor=request.user, facility=request_facility(request)
        )
        return Response(LicenceSerializer(licence).data)
