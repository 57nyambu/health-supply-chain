from types import SimpleNamespace
from typing import Any, cast

import pytest
from django.contrib.sessions.backends.db import SessionStore
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.access.drf import (
    AUTHENTICATED,
    SESSION_FACILITY_KEY,
    PolicyPermission,
    object_facility,
    request_facility,
)
from apps.facilities.tests.factories import FacilityFactory

pytestmark = pytest.mark.django_db


def ns(**fields: Any) -> Any:
    return cast(Any, SimpleNamespace(**fields))


class MethodPolicyView(APIView):
    policy = {"GET": "inventory.store.read", "POST": "inventory.store.manage"}

    def get(self, request):
        return Response({"facility": request_facility(request)})

    def post(self, request):
        return Response({"ok": True})


class CallablePolicyView(APIView):
    policy = staticmethod(lambda view, request: AUTHENTICATED if request.GET.get("open") else None)

    def get(self, request):
        return Response({"ok": True})


def call(view, user, method="get", session=None, **params):
    factory = APIRequestFactory()
    request = getattr(factory, method)("/x", params)
    request.session = session if session is not None else SessionStore()
    force_authenticate(request, user=user)
    return view.as_view()(request)


def test_method_policies(make_user, facility, grant):
    keeper, viewer = make_user(), make_user()
    grant(keeper, "store_keeper", facility)
    grant(viewer, "report_viewer", facility)
    assert call(MethodPolicyView, keeper).status_code == 200
    assert call(MethodPolicyView, keeper, "post").status_code == 200
    assert call(MethodPolicyView, viewer).status_code == 403
    assert call(MethodPolicyView, keeper, "put").status_code == 403  # no policy for PUT


def test_callable_policy(make_user, facility, grant):
    user = make_user()
    assert call(CallablePolicyView, user, open="1").status_code == 200
    assert call(CallablePolicyView, user).status_code == 403


def test_user_in_several_facilities_must_choose_one(make_user, facility, grant):
    second = FacilityFactory.create()
    user = make_user()
    grant(user, "store_keeper", facility)
    grant(user, "report_viewer", second)
    assert call(MethodPolicyView, user).status_code == 403  # ambiguous: no facility chosen
    session = SessionStore()
    session[SESSION_FACILITY_KEY] = facility.pk
    response = call(MethodPolicyView, user, session=session)
    assert response.status_code == 200
    assert response.data == {"facility": facility.pk}
    session[SESSION_FACILITY_KEY] = second.pk  # chosen facility where the role lacks the code
    assert call(MethodPolicyView, user, session=session).status_code == 403


def test_a_chosen_facility_without_assignment_is_ignored(make_user, facility, grant):
    user = make_user()
    grant(user, "store_keeper", facility)
    session = SessionStore()
    session[SESSION_FACILITY_KEY] = FacilityFactory.create().pk
    response = call(MethodPolicyView, user, session=session)
    assert response.data == {"facility": facility.pk}  # falls back to the only real facility


def test_object_level_check_uses_the_objects_facility(make_user, facility, grant):
    user = make_user()
    grant(user, "store_keeper", facility)
    permission = PolicyPermission()
    request = ns(method="GET", user=user)
    view = MethodPolicyView()
    view.action = None  # type: ignore[attr-defined]
    assert permission.has_object_permission(request, view, ns(facility_id=facility.pk))
    other = FacilityFactory.create()
    assert not permission.has_object_permission(request, view, ns(facility_id=other.pk))
    assert permission.has_object_permission(request, view, ns())  # not facility-bound
    assert object_facility(view, ns(facility_id=None)) is None


def test_service_principals_skip_object_facility_checks():
    permission = PolicyPermission()
    request = ns(method="GET", user=ns(is_service_account=True))
    view = MethodPolicyView()
    view.action = None  # type: ignore[attr-defined]
    assert permission.has_object_permission(request, view, ns(facility_id=1))
