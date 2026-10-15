from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import user_tier, user_warehouse_id

from .models import RTInventoryAlert
from .serializers import RTInventoryAlertSerializer


class InventoryAlertsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		tier = user_tier(request.user)
		qs = RTInventoryAlert.objects.select_related('product', 'warehouse').all()

		if tier == 2:
			warehouse_id = user_warehouse_id(request.user)
			if warehouse_id:
				qs = qs.filter(warehouse_id=warehouse_id)
			else:
				qs = RTInventoryAlert.objects.none()
		elif tier not in (1, 3):
			raise PermissionDenied('You do not have access to inventory alerts.')

		serializer = RTInventoryAlertSerializer(qs, many=True)
		return Response(serializer.data)
