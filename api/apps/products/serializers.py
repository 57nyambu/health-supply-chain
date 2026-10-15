from rest_framework import serializers
from .models import Category, Product, ProductImage, Inventory

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary', 'caption']

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    vat_amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ('sku', 'last_restocked')

class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'name', 'short_name', 'category', 
            'barcode', 'product_type', 'buying_price',
            'selling_price', 'wholesale_price', 'reorder_level'
        ]

class InventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    needs_restock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inventory
        fields = '__all__'