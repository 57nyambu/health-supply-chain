from django.contrib import admin
from .models import FacilityDailyStats, FacilityAlert


@admin.register(FacilityDailyStats)
class FacilityDailyStatsAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'date', 'patient_footfall', 'bed_occupancy_rate', 'attendance_rate')
    list_filter = ('warehouse', 'date')
    date_hierarchy = 'date'


@admin.register(FacilityAlert)
class FacilityAlertAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'alert_type', 'severity', 'resolved', 'created_at')
    list_filter = ('alert_type', 'severity', 'resolved', 'warehouse')
    search_fields = ('message',)