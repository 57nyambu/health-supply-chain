from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Branch, Warehouse, BinLocation, StockTransfer
from .serializers import (
    BranchSerializer,
    WarehouseSerializer,
    BinLocationSerializer,
    StockTransferSerializer,
    StockTransferCreateSerializer
)
from .permissions import IsWarehouseManager, CanApproveTransfers

class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.filter(is_active=True)
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAdminUser]

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['ADMIN', 'BRANCH_MANAGER']:
            return Warehouse.objects.all()
        return Warehouse.objects.filter(branch__manager=user)

class BinLocationViewSet(viewsets.ModelViewSet):
    queryset = BinLocation.objects.all()
    serializer_class = BinLocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            return BinLocation.objects.filter(warehouse_id=warehouse_id)
        return BinLocation.objects.all()

class StockTransferViewSet(viewsets.ModelViewSet):
    queryset = StockTransfer.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return StockTransferCreateSerializer
        return StockTransferSerializer

    def perform_create(self, serializer):
        serializer.save(initiated_by=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        transfer = self.get_object()
        if not request.user.has_perm('warehouses.approve_transfers'):
            return Response(
                {'error': 'You do not have permission to approve transfers'},
                status=status.HTTP_403_FORBIDDEN
            )
        transfer.status = 'APPROVED'
        transfer.approved_by = request.user
        transfer.save()
        return Response({'status': 'transfer approved'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        transfer = self.get_object()
        if not IsWarehouseManager().has_object_permission(request, self, transfer.to_warehouse):
            return Response(
                {'error': 'Only warehouse managers can complete transfers'},
                status=status.HTTP_403_FORBIDDEN
            )
        transfer.status = 'RECEIVED'
        transfer.save()
        return Response({'status': 'transfer received'})