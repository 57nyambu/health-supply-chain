from rest_framework.routers import SimpleRouter

from .views import PatientMergeViewSet, PatientViewSet

router = SimpleRouter()
router.register("merges", PatientMergeViewSet, basename="patient-merge")
router.register("", PatientViewSet, basename="patient")

urlpatterns = router.urls
