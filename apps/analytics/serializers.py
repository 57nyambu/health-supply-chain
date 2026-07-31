from rest_framework import serializers

from .models import RTInventoryAlert


class RTInventoryAlertSerializer(serializers.ModelSerializer):
	product_name = serializers.CharField(source='product.name', read_only=True)
	warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

	class Meta:
		model = RTInventoryAlert
		fields = [
			'id',
			'product',
			'product_name',
			'warehouse',
			'warehouse_name',
			'current_stock',
			'resolved',
			'created_at',
		]
