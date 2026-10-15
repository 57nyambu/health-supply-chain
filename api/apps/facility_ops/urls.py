from django.urls import path

from .views import FacilityAlertsView, FacilityStatsView

urlpatterns = [
    path('stats/', FacilityStatsView.as_view(), name='facility-stats'),
    path('alerts/', FacilityAlertsView.as_view(), name='facility-alerts'),
]
