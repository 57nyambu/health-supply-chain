from django.urls import path
from .views import InventoryAlertsView

urlpatterns = [
    path('inventory-alerts/', InventoryAlertsView.as_view(), name='inventory-alerts'),
]