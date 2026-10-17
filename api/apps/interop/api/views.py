"""HIE registry lookups for set-up screens (P3-SHA-01; KE-DHA-04)."""

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.drf import require_facility
from apps.audit.services import record
from apps.core.problems import ApiProblem
from apps.interop.hie.errors import HieConfigurationError, HieError
from apps.interop.registries import IDENTIFIER_TYPES, facility_record


class RegistryUnavailable(ApiProblem):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "The national Facility Registry is not answering. Try again later."
    default_code = "registry_unavailable"


class FacilityQuerySerializer(serializers.Serializer[Any]):
    identifier = serializers.CharField(max_length=60)
    type = serializers.ChoiceField(choices=list(IDENTIFIER_TYPES), default="fid", required=False)


class FacilityRecordSerializer(serializers.Serializer[Any]):
    fid = serializers.CharField()
    fr_code = serializers.CharField()
    official_name = serializers.CharField()
    keph_level = serializers.CharField()
    licence_status = serializers.CharField()
    licence_valid_to = serializers.DateField(allow_null=True)
    sha_contract_status = serializers.CharField()
    operational_status = serializers.CharField()
    contracted_services = serializers.ListField(child=serializers.CharField())
    sha_active = serializers.BooleanField()


class FacilityRegistryView(APIView):
    """Look a facility up in the national Facility Registry (FID, KEPH level, SHA contract)."""

    policy = "facilities.facility.manage"

    @extend_schema(parameters=[FacilityQuerySerializer], responses=FacilityRecordSerializer)
    def get(self, request: Request) -> Response:
        query = FacilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        facility = require_facility(request)
        try:
            found = facility_record(
                query.validated_data["identifier"], query.validated_data["type"]
            )
        except HieConfigurationError as exc:
            raise RegistryUnavailable(str(exc)) from exc
        except HieError as exc:
            raise RegistryUnavailable() from exc
        record(
            "interop.facility_registry.searched",
            request.user,
            facility=facility,
            detail={"found": found is not None, "type": query.validated_data["type"]},
        )
        if found is None:
            raise NotFound("The Facility Registry has no facility with this identifier.")
        data = {**found.__dict__, "sha_active": found.sha_active}
        return Response(FacilityRecordSerializer(data).data)
