from django.urls import path
from .views import POSView, ProcessPaymentView

urlpatterns = [
    path('pos/', POSView.as_view(), name='pos'),
    path('process-payment/', ProcessPaymentView.as_view(), name='process_payment'),
]