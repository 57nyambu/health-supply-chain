from rest_framework import serializers
from .models import FacilityDailyStats, FacilityAlert


class FacilityDailyStatsSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    bed_occupancy_rate = serializers.ReadOnlyField()
    attendance_rate = serializers.ReadOnlyField()

    class Meta:
        model = FacilityDailyStats
        fields = [
            'id', 'warehouse', 'warehouse_name', 'date',
            'patient_footfall', 'beds_total', 'beds_occupied',
            'doctors_scheduled', 'doctors_present',
            'bed_occupancy_rate', 'attendance_rate',
        ]


class FacilityAlertSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = FacilityAlert
        fields = [
            'id', 'warehouse', 'warehouse_name', 'alert_type', 'message',
            'severity', 'resolved', 'resolved_at', 'created_at',
        ]
        read_only_fields = ['resolved_at', 'created_at']


class PublicFacilityStatsSerializer(serializers.ModelSerializer):
    """Curated subset for the open /api/v1/public/ API — no raw inventory figures."""
    facility_name = serializers.CharField(source='warehouse.name', read_only=True)
    bed_occupancy_rate = serializers.ReadOnlyField()
    attendance_rate = serializers.ReadOnlyField()

    class Meta:
        model = FacilityDailyStats
        fields = ['facility_name', 'date', 'patient_footfall', 'bed_occupancy_rate', 'attendance_rate']


class PublicFacilityAlertSerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = FacilityAlert
        fields = ['facility_name', 'alert_type', 'severity', 'message', 'created_at']