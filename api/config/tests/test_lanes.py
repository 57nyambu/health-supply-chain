"""Parallel-lane registrations (ADR-024): the shared code merges them, and each lane's
entries are valid, unique and kept in its own namespace."""

from types import SimpleNamespace

import pytest
from django.conf import settings
from django.urls import get_resolver

from apps.access.catalogue import all_permissions
from apps.access.roles import RoleDef, with_lane_grants
from config import lanes
from config.lanes import phase2, phase3


def fake_lane(**overrides):
    values = {
        "INSTALLED_APPS": [],
        "URLS": [],
        "SEED_STEPS": [],
        "CELERY_BEAT_SCHEDULE": {},
        "ROLE_GRANTS": {},
        "settings": lambda env: {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_lane_registrations_are_merged_in_lane_order(monkeypatch):
    two = fake_lane(
        INSTALLED_APPS=["apps.two"],
        URLS=[("api/v1/two/", "apps.two.urls")],
        SEED_STEPS=["apps.two.seed"],
        CELERY_BEAT_SCHEDULE={"p2-job": {"task": "t2"}},
        ROLE_GRANTS={"cashier": ("a.b.c",)},
        settings=lambda env: {"TWO_MODE": "fake"},
    )
    three = fake_lane(
        INSTALLED_APPS=["apps.three"],
        SEED_STEPS=["apps.three.seed"],
        ROLE_GRANTS={"cashier": ("d.e.f",)},
        settings=lambda env: {"THREE_MODE": "fake"},
    )
    monkeypatch.setattr(lanes, "LANES", (two, three))
    assert lanes.installed_apps() == ["apps.two", "apps.three"]
    assert lanes.url_mounts() == [("api/v1/two/", "apps.two.urls")]
    assert lanes.seed_steps() == ["apps.two.seed", "apps.three.seed"]
    assert lanes.beat_schedule() == {"p2-job": {"task": "t2"}}
    assert lanes.settings(None) == {"TWO_MODE": "fake", "THREE_MODE": "fake"}
    assert lanes.role_grants() == {"cashier": ("a.b.c", "d.e.f")}


def test_lane_grants_extend_existing_roles_only():
    base = [RoleDef("cashier", "Cashier", "", ("payments.receive.cash",))]
    [cashier] = with_lane_grants(base, {"cashier": ("payments.receive.cash", "payments.shift.own")})
    assert cashier.grants == ("payments.receive.cash", "payments.shift.own")
    with pytest.raises(ValueError, match="unknown roles"):
        with_lane_grants(base, {"no_such_role": ("x.y.z",)})


@pytest.mark.parametrize("lane, prefix", [(phase2, "p2-"), (phase3, "p3-")])
def test_each_lane_keeps_to_its_namespace(lane, prefix):
    assert len(set(lane.INSTALLED_APPS)) == len(lane.INSTALLED_APPS)
    assert all(app.startswith("apps.") for app in lane.INSTALLED_APPS)
    assert all(name.startswith(prefix) for name in lane.CELERY_BEAT_SCHEDULE)
    for url_prefix, _module in lane.URLS:
        assert url_prefix.startswith("api/v1/") and url_prefix.endswith("/")


def test_lanes_do_not_collide_with_each_other_or_phase_1():
    p2, p3 = set(phase2.INSTALLED_APPS), set(phase3.INSTALLED_APPS)
    assert not p2 & p3
    phase1 = set(settings.INSTALLED_APPS) - p2 - p3
    assert not (p2 | p3) & phase1
    prefixes = [p for p, _ in phase2.URLS + phase3.URLS]
    assert len(prefixes) == len(set(prefixes))
    mounted = {str(p.pattern) for p in get_resolver().url_patterns}
    assert set(prefixes) <= mounted


def test_lane_grants_name_known_permissions():
    """Exact codes, or `domain.resource.*` patterns that match at least one known code."""
    known = set(all_permissions())
    for codes in lanes.role_grants().values():
        for code in codes:
            if code.endswith(".*"):
                assert any(k.startswith(code[:-1]) for k in known), code
            else:
                assert code in known, code
