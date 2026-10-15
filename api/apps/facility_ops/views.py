from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import user_tier, user_warehouse_id

from .models import FacilityAlert, FacilityDailyStats
from .serializers import FacilityAlertSerializer, FacilityDailyStatsSerializer


class FacilityStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_scoped_queryset(self, request):
        tier = user_tier(request.user)
        queryset = FacilityDailyStats.objects.select_related('warehouse').all()

        if tier == 1:
            warehouse = request.query_params.get('warehouse')
            if warehouse:
                queryset = queryset.filter(warehouse_id=warehouse)
            return queryset

        if tier == 2:
            warehouse_id = user_warehouse_id(request.user)
            if not warehouse_id:
                return FacilityDailyStats.objects.none()
            return queryset.filter(warehouse_id=warehouse_id)

        if tier == 3:
            warehouse = request.query_params.get('warehouse')
            if warehouse:
                queryset = queryset.filter(warehouse_id=warehouse)
            return queryset

        raise PermissionDenied('You do not have access to facility stats.')

    def get(self, request):
        queryset = self._get_scoped_queryset(request)
        serializer = FacilityDailyStatsSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        tier = user_tier(request.user)
        if tier not in (1, 2):
            raise PermissionDenied('Only Tier 1 and Tier 2 users can submit facility stats.')

        payload = request.data.copy()
        if tier == 2:
            scoped_warehouse_id = user_warehouse_id(request.user)
            if not scoped_warehouse_id:
                raise ValidationError('Tier 2 user is not assigned to a facility warehouse.')

            incoming_warehouse = payload.get('warehouse')
            if incoming_warehouse:
                try:
                    incoming_warehouse_id = int(incoming_warehouse)
                except (TypeError, ValueError) as exc:
                    raise ValidationError('warehouse must be a valid numeric id.') from exc

                if incoming_warehouse_id != scoped_warehouse_id:
                    raise PermissionDenied('Tier 2 users can only submit stats for their own facility.')

            payload['warehouse'] = scoped_warehouse_id

        serializer = FacilityDailyStatsSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FacilityAlertsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tier = user_tier(request.user)
        queryset = FacilityAlert.objects.select_related('warehouse').all()

        if tier == 2:
            scoped_warehouse_id = user_warehouse_id(request.user)
            if not scoped_warehouse_id:
                queryset = FacilityAlert.objects.none()
            else:
                queryset = queryset.filter(warehouse_id=scoped_warehouse_id)
        elif tier not in (1, 3):
            raise PermissionDenied('You do not have access to facility alerts.')

        serializer = FacilityAlertSerializer(queryset, many=True)
        return Response(serializer.data)