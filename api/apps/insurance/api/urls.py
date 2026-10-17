from rest_framework.routers import SimpleRouter

from .views import CoverageViewSet, PayerConsentViewSet, SchemeViewSet

router = SimpleRouter()
router.register("schemes", SchemeViewSet, basename="insurance-scheme")
router.register("coverages", CoverageViewSet, basename="insurance-coverage")
router.register("consents", PayerConsentViewSet, basename="insurance-consent")

urlpatterns = router.urls
