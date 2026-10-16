from rest_framework.routers import SimpleRouter

from .views import ApprovalViewSet, AssignmentViewSet, RoleViewSet

router = SimpleRouter()
router.register("roles", RoleViewSet, basename="role")
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("approvals", ApprovalViewSet, basename="approval")

urlpatterns = router.urls
