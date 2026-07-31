from rest_framework import serializers


class AssistantRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=1000)


class OCRIntakeSerializer(serializers.Serializer):
    image = serializers.ImageField()


class ForecastResponseSerializer(serializers.Serializer):
    product = serializers.CharField()
    warehouse = serializers.CharField()
    current_stock = serializers.IntegerField()
    avg_daily_consumption = serializers.IntegerField()
    forecast_days_remaining = serializers.IntegerField()
    recommendation = serializers.CharField()
