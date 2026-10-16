from rest_framework.routers import SimpleRouter

from .views import ApprovalViewSet, AssignmentViewSet, BreakGlassViewSet, RoleViewSet

router = SimpleRouter()
router.register("roles", RoleViewSet, basename="role")
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("approvals", ApprovalViewSet, basename="approval")
router.register("break-glass", BreakGlassViewSet, basename="break-glass")

urlpatterns = router.urls
