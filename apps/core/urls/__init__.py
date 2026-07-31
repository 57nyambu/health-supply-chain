from django.urls import path, include

urlpatterns = [
    path('auth/', include('apps.core.urls.auth')),
    path('', include('apps.core.urls.mgt')),
]