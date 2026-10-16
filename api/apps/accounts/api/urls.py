from django.urls import path

from .views import CsrfView, LoginView, LogoutView, MeFacilityView, MeView, PasswordChangeView

auth_urlpatterns = [
    path("csrf", CsrfView.as_view(), name="auth-csrf"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("password", PasswordChangeView.as_view(), name="auth-password"),
]

me_urlpatterns = [
    path("me", MeView.as_view(), name="me"),
    path("me/facility", MeFacilityView.as_view(), name="me-facility"),
]
