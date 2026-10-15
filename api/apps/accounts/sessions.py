"""Server-side session tracking and revocation (DESIGN §7.2, §7.6)."""

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.sessions.models import Session
from django.db import transaction
from django.dispatch import receiver
from django.utils import timezone

from apps.accounts.models import UserSession


@receiver(user_logged_in)
def _track_login(sender, request, user, **kwargs):
    if request is None or not hasattr(request, "session"):
        return
    if request.session.session_key is None:
        request.session.save()
    UserSession.objects.create(
        session_key=request.session.session_key, user=user, last_activity_at=timezone.now()
    )


@receiver(user_logged_out)
def _track_logout(sender, request, user, **kwargs):
    if user is None or request is None or not getattr(request, "session", None):
        return
    end_sessions(user, reason=UserSession.EndReason.LOGOUT, session_key=request.session.session_key)


@transaction.atomic
def end_sessions(user, *, reason: str, session_key: str | None = None) -> int:
    """End open sessions of ``user`` (one, or all) and delete them server-side immediately."""
    open_sessions = UserSession.objects.select_for_update().filter(user=user, ended_at__isnull=True)
    if session_key is not None:
        open_sessions = open_sessions.filter(session_key=session_key)
    keys = list(open_sessions.values_list("session_key", flat=True))
    Session.objects.filter(session_key__in=keys).delete()
    return open_sessions.update(ended_at=timezone.now(), end_reason=reason)
