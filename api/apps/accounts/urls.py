from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .api.licences import LicenceViewSet
from .views import UserViewSet, WorkerProfileViewSet

router = SimpleRouter()
router.register(r"users", UserViewSet)
router.register(r"profiles", WorkerProfileViewSet)
router.register(r"licences", LicenceViewSet, basename="licence")

urlpatterns = [
    path("", include(router.urls)),
]
