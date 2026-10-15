from django.urls import path

from .views import (
    AssistantView,
    ForecastView,
    OCRIntakeView,
    RedistributionSuggestionsView,
)

urlpatterns = [
    path('assistant/', AssistantView.as_view(), name='ai-assistant'),
    path('ocr-intake/', OCRIntakeView.as_view(), name='ai-ocr-intake'),
    path('forecast/<int:warehouse_id>/<int:product_id>/', ForecastView.as_view(), name='ai-forecast'),
    path('redistribution-suggestions/', RedistributionSuggestionsView.as_view(), name='ai-redistribution-suggestions'),
]
