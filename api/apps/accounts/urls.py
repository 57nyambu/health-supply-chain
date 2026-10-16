from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import UserViewSet, WorkerProfileViewSet

router = SimpleRouter()
router.register(r"users", UserViewSet)
router.register(r"profiles", WorkerProfileViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
