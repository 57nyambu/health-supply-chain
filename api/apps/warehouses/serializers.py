from rest_framework import serializers
from .models import Branch, Warehouse, BinLocation, StockTransfer

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class WarehouseSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    
    class Meta:
        model = Warehouse
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class BinLocationSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    
    class Meta:
        model = BinLocation
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class StockTransferSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    from_warehouse_name = serializers.CharField(source='from_warehouse.name', read_only=True)
    to_warehouse_name = serializers.CharField(source='to_warehouse.name', read_only=True)
    initiated_by_name = serializers.CharField(source='initiated_by.get_full_name', read_only=True)
    
    class Meta:
        model = StockTransfer
        fields = '__all__'
        read_only_fields = (
            'created_at', 
            'updated_at', 
            'reference_no',
            'initiated_by',
            'verified_at'
        )

class StockTransferCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransfer
        fields = [
            'product',
            'transfer_type',
            'from_warehouse',
            'to_warehouse',
            'from_bin',
            'to_bin',
            'quantity',
            'notes'
        ]