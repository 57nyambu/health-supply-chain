from rest_framework.routers import SimpleRouter

from .views import DataSubjectRequestViewSet, PatientMergeViewSet, PatientViewSet

router = SimpleRouter()
router.register("merges", PatientMergeViewSet, basename="patient-merge")
router.register("dsar", DataSubjectRequestViewSet, basename="dsar")
router.register("", PatientViewSet, basename="patient")

urlpatterns = router.urls
