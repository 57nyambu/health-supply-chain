from django.contrib import admin

from .models import Customer, Order, OrderItem, Receipt


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
	list_display = ('name', 'phone', 'email', 'is_active')
	search_fields = ('name', 'phone', 'email')


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('order_number', 'status', 'payment_method', 'total', 'created_at')
	list_filter = ('status', 'payment_method', 'created_at')
	search_fields = ('order_number', 'customer__name', 'customer__phone')
	inlines = [OrderItemInline]


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
	list_display = ('receipt_number', 'order', 'sms_sent', 'sms_status', 'issued_at')
	search_fields = ('receipt_number', 'order__order_number')


admin.site.register(OrderItem)
from django.contrib import admin

# Register your models here.
