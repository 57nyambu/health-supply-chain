from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import PriceListViewSet, QuoteView, ServiceViewSet

router = SimpleRouter()
router.register("services", ServiceViewSet, basename="billing-service")
router.register("price-lists", PriceListViewSet, basename="billing-pricelist")

urlpatterns = [path("quote/", QuoteView.as_view(), name="billing-quote"), *router.urls]
