from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    BoardDisplayView,
    BoardViewSet,
    GatePolicyViewSet,
    QueueViewSet,
    TicketViewSet,
    VisitViewSet,
)

router = SimpleRouter()
router.register("queues", QueueViewSet, basename="visits-queue")
router.register("tickets", TicketViewSet, basename="visits-ticket")
router.register("gate-policies", GatePolicyViewSet, basename="visits-gatepolicy")
router.register("boards", BoardViewSet, basename="visits-board")
router.register("", VisitViewSet, basename="visits-visit")

urlpatterns = [
    path("board-display/", BoardDisplayView.as_view(), name="visits-board-display"),
    *router.urls,
]
