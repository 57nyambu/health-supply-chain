"""Default deny, enforced over the whole URLconf (P1-UAC-03, DESIGN §7.3).

Every DRF view must keep PolicyPermission and declare a known permission code (or an
allowed sentinel) for every method/action it serves. Non-DRF views are allowed only
on the explicit allowlist below.
"""

import re
from collections.abc import Iterator

import pytest
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.views import APIView

from apps.access.catalogue import is_known
from apps.access.drf import AUTHENTICATED, PUBLIC, PolicyPermission, declared_policy

# Plain Django views that need no policy, with the reason.
NON_DRF_ALLOWLIST = {
    "healthz": "liveness probe, no data",
    "readyz": "readiness probe, component status only",
}
# DRF view/action pairs allowed to be PUBLIC (no authentication).
PUBLIC_ALLOWLIST = {
    ("AuthViewSet", "login"),
    ("AuthViewSet", "logout"),
}


def walk(patterns, prefix="") -> Iterator[tuple[str, URLPattern]]:
    for entry in patterns:
        if isinstance(entry, URLResolver):
            yield from walk(entry.url_patterns, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern):
            yield prefix + str(entry.pattern), entry


def drf_targets(callback) -> Iterator[tuple[type[APIView], str | None, str]]:
    view_class = callback.cls
    actions = getattr(callback, "actions", None)
    if actions:
        for method, action in list(actions.items()):
            # Methods excluded by http_method_names are answered 405 and never reach a handler.
            if method not in ("options", "head") and method in view_class.http_method_names:
                yield view_class, action, method
        return
    for method in view_class.http_method_names:
        if method not in ("options", "head", "trace") and hasattr(view_class, method):
            yield view_class, None, method


def all_routes():
    return list(walk(get_resolver().url_patterns))


def test_urlconf_has_routes():
    assert len(all_routes()) > 20


def test_every_view_has_policy():
    problems = []
    for route, pattern in all_routes():
        callback = pattern.callback
        if not hasattr(callback, "cls"):
            if pattern.name not in NON_DRF_ALLOWLIST:
                problems.append(
                    f"{route}: plain Django view {callback.__name__} is not allowlisted"
                )
            continue
        for view_class, action, method in drf_targets(callback):
            label = f"{route} {method.upper()} {view_class.__name__}.{action or method}"
            if not any(issubclass(p, PolicyPermission) for p in view_class.permission_classes):
                problems.append(f"{label}: permission_classes drops PolicyPermission")
            policy = declared_policy(view_class, action, method)
            if policy is None:
                problems.append(f"{label}: no policy declared")
            elif callable(policy):
                continue
            elif policy == PUBLIC and (view_class.__name__, action) not in PUBLIC_ALLOWLIST:
                problems.append(f"{label}: PUBLIC is not allowlisted")
            elif policy not in (PUBLIC, AUTHENTICATED) and not is_known(policy):
                problems.append(f"{label}: unknown permission code {policy!r}")
    assert problems == []


@pytest.mark.req("KE-DPA-06")
@pytest.mark.django_db
def test_unauthenticated_requests_are_refused_everywhere(client):
    """Every non-public API route refuses anonymous callers (401/403), never 200/500."""
    failures = []
    for route, pattern in all_routes():
        if not route.startswith("api/") or not hasattr(pattern.callback, "cls"):
            continue
        url = re.sub(r"\(\?P<\w+>[^)]*\)|<(?:\w+:)?\w+>", "1", route)
        url = "/" + url.replace("^", "").replace("$", "")
        for view_class, action, method in drf_targets(pattern.callback):
            if declared_policy(view_class, action, method) == PUBLIC:
                continue
            response = getattr(client, method)(url)
            if response.status_code not in (401, 403):
                failures.append(f"{method.upper()} {url} -> {response.status_code}")
    assert failures == []


class UndeclaredView(APIView):
    def get(self, request):  # pragma: no cover - never reached
        raise AssertionError("must be denied before the handler runs")


class UnknownCodeView(APIView):
    policy = "clinical.everything.read"

    def get(self, request):  # pragma: no cover - never reached
        raise AssertionError("must be denied")


@pytest.mark.django_db
@pytest.mark.parametrize("view", [UndeclaredView, UnknownCodeView])
def test_views_without_a_valid_policy_deny_every_request(rf, make_user, facility, grant, view):
    user = make_user()
    grant(user, "facility_admin", facility)
    request = rf.get("/x")
    request.user = user
    request.session = {}
    response = view.as_view()(request)
    assert response.status_code == 403
