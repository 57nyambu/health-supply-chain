from rest_framework.routers import SimpleRouter

from .views import BedViewSet, DepartmentViewSet, FacilityViewSet, ServicePointViewSet, WardViewSet

router = SimpleRouter()
router.register("facilities", FacilityViewSet, basename="facility")
router.register("departments", DepartmentViewSet, basename="department")
router.register("service-points", ServicePointViewSet, basename="service-point")
router.register("wards", WardViewSet, basename="ward")
router.register("beds", BedViewSet, basename="bed")

urlpatterns = router.urls
