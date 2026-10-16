from django.urls import path

from .views import (
    CsrfView,
    LockView,
    LoginView,
    LogoutView,
    MeFacilityView,
    MeView,
    MfaVerifyView,
    PasswordChangeView,
    PinView,
    RecoveryCodesView,
    SwitchUserView,
    TotpConfirmView,
    TotpSetupView,
    UnlockView,
)

auth_urlpatterns = [
    path("csrf", CsrfView.as_view(), name="auth-csrf"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("password", PasswordChangeView.as_view(), name="auth-password"),
    path("mfa/verify", MfaVerifyView.as_view(), name="auth-mfa-verify"),
    path("lock", LockView.as_view(), name="auth-lock"),
    path("unlock", UnlockView.as_view(), name="auth-unlock"),
    path("switch", SwitchUserView.as_view(), name="auth-switch"),
    path("pin", PinView.as_view(), name="auth-pin"),
    path("mfa/totp/setup", TotpSetupView.as_view(), name="auth-mfa-totp-setup"),
    path("mfa/totp/confirm", TotpConfirmView.as_view(), name="auth-mfa-totp-confirm"),
    path("mfa/recovery-codes", RecoveryCodesView.as_view(), name="auth-mfa-recovery-codes"),
]

me_urlpatterns = [
    path("me", MeView.as_view(), name="me"),
    path("me/facility", MeFacilityView.as_view(), name="me-facility"),
]
