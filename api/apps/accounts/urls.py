from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AuthViewSet, UserViewSet, WorkerProfileViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"profiles", WorkerProfileViewSet)
router.register(r"auth", AuthViewSet, basename="auth")

urlpatterns = [
    path("", include(router.urls)),
]
