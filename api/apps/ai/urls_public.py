from django.urls import path

from .views import PublicAlertsView, PublicFacilitiesView, PublicFacilityStatsView

urlpatterns = [
    path('facilities/', PublicFacilitiesView.as_view(), name='public-facilities'),
    path('alerts/', PublicAlertsView.as_view(), name='public-alerts'),
    path('facility-stats/<int:facility_id>/', PublicFacilityStatsView.as_view(), name='public-facility-stats'),
]
