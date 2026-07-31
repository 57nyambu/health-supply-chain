from django.contrib import admin
from .models import Category, Product, ProductImage, Inventory

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'vat_category')
    list_filter = ('vat_category',)
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'sku', 
        'category', 
        'selling_price', 
        'is_active'
    )
    list_filter = ('category', 'is_active', 'product_type')
    search_fields = ('name', 'sku', 'barcode')
    readonly_fields = ('sku',)

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'is_primary')
    list_filter = ('is_primary',)
    raw_id_fields = ('product',)

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity', 'last_checked')
    list_filter = ('warehouse',)
    search_fields = ('product__name', 'product__sku')
    readonly_fields = ('last_checked',)