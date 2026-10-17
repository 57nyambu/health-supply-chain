from django.urls import path

from .views import FacilityRegistryView

urlpatterns = [
    path("facility-registry/", FacilityRegistryView.as_view(), name="interop-facility-registry"),
]
