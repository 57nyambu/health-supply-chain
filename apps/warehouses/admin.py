from django.contrib import admin
from .models import Branch, Warehouse, BinLocation, StockTransfer

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'county', 'kra_pin', 'is_active')
    list_filter = ('county', 'is_active')
    search_fields = ('name', 'code', 'kra_pin')

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'branch', 'warehouse_type', 'manager')
    list_filter = ('warehouse_type', 'branch')
    search_fields = ('name', 'code')

@admin.register(BinLocation)
class BinLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'warehouse', 'bin_type')
    list_filter = ('bin_type', 'warehouse')
    search_fields = ('name', 'barcode')

@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('reference_no', 'product', 'status', 'from_warehouse', 'to_warehouse')
    list_filter = ('status', 'transfer_type')
    search_fields = ('reference_no', 'product__name')
    readonly_fields = ('reference_no',)