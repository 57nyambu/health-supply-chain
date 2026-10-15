from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.core.urls.auth")),
    path("", include("apps.core.urls.mgt")),
]
