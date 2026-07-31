from django.urls import path
from apps.core.views import pos

urlpatterns = [
    path('', pos, name='pos_interface'),
    ]