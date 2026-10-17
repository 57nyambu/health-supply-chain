from rest_framework.routers import SimpleRouter

from .views import CoverageViewSet, SchemeViewSet

router = SimpleRouter()
router.register("schemes", SchemeViewSet, basename="insurance-scheme")
router.register("coverages", CoverageViewSet, basename="insurance-coverage")

urlpatterns = router.urls
