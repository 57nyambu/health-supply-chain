from django.contrib import admin
from .models import Notification, InventoryAlert

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'subject', 'is_read', 'created_at', 'sent_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('subject', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'sent_at')

@admin.register(InventoryAlert)
class InventoryAlertAdmin(admin.ModelAdmin):
    list_display = ('product', 'alert_type', 'message', 'resolved', 'created_at', 'resolved_at')
    list_filter = ('alert_type', 'resolved')
    search_fields = ('message',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'resolved_at')