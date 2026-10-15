import importlib
import json
import threading
import uuid
from datetime import timedelta

import pytest
import time_machine
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from apps.audit import context, services
from apps.audit.models import AuditAnchor, AuditChainHead, AuditEvent
from apps.audit.services import GENESIS_HASH, anchor_file_path, anchor_finished_chains, record
from apps.audit.verify import verify_chains

pytestmark = [pytest.mark.django_db, pytest.mark.req("KE-DPA-06")]

revoke_migration = importlib.import_module("apps.audit.migrations.0003_revoke_app_role_mutation")


@pytest.fixture(autouse=True)
def isolated_data_dir(settings, tmp_path_factory):
    settings.DATA_DIR = tmp_path_factory.mktemp("data")


def _mutable(table="audit_auditevent"):
    with connection.cursor() as cursor:
        cursor.execute(f"ALTER TABLE {table} DISABLE TRIGGER {table}_append_only")


def test_events_form_a_hash_chain():
    first = record("test.thing.created", resource=("test.thing", "1"), detail={"count": 1})
    second = record("test.thing.updated", resource=("test.thing", "1"))
    assert (first.seq, second.seq) == (1, 2)
    assert first.prev_hash == GENESIS_HASH
    assert second.prev_hash == first.hash
    assert services.compute_hash(second.prev_hash, second) == second.hash
    head = AuditChainHead.objects.get(facility_id=0, chain_date=first.chain_date)
    assert (head.last_seq, head.last_hash) == (2, second.hash)


def test_context_is_captured(django_user_model):
    user = django_user_model.objects.create_user(email="clerk@example.test")
    context.update(ip="10.0.0.5", user_agent="pytest", workstation_id="ws-7", facility_id=3)
    try:
        event = record("test.read", actor=user)
    finally:
        context.update(ip=None, user_agent="", workstation_id="", facility_id=None)
    assert (event.actor_id, event.ip, event.workstation_id, event.facility_id) == (
        user.pk,
        "10.0.0.5",
        "ws-7",
        3,
    )


@pytest.mark.req("KE-DPA-01")
def test_detail_refuses_personal_data_and_scrubs_strings():
    with pytest.raises(ValueError, match="personal data"):
        record("test.bad", detail={"patient_name": "Wanjiku"})
    event = record(
        "test.ok", detail={"reason_code": "dup", "order_ref": None, "msg": "call 0712345678"}
    )
    assert event.detail["msg"] == "call [number]"


def test_facilities_have_separate_chains():
    a = record("x.y.z", facility=1)
    b = record("x.y.z", facility=2)
    assert a.seq == b.seq == 1
    assert a.prev_hash == b.prev_hash == GENESIS_HASH


def test_new_day_links_to_previous_day():
    yesterday = record("x.y.day1", facility=4)
    with time_machine.travel(timezone.now() + timedelta(days=1)):
        today = record("x.y.day2", facility=4)
    assert today.seq == 1
    assert today.prev_hash == yesterday.hash
    assert verify_chains()[1] == []


def test_database_rejects_update_and_delete():
    event = record("x.y.z")
    with pytest.raises(DatabaseError, match="append-only"), transaction.atomic():
        AuditEvent.objects.filter(pk=event.pk).update(action="tampered")
    with pytest.raises(DatabaseError, match="append-only"), transaction.atomic():
        AuditEvent.objects.filter(pk=event.pk).delete()


def test_verify_passes_on_an_intact_chain():
    for index in range(5):
        record("x.y.z", detail={"i": index})
    checked, problems = verify_chains()
    assert checked == 5
    assert problems == []
    call_command("audit_verify")


def test_verify_detects_a_modified_row():
    events = [record("x.y.z", detail={"i": i}) for i in range(4)]
    _mutable()
    AuditEvent.objects.filter(pk=events[1].pk).update(action="x.y.tampered")
    kinds = {p.kind for p in verify_chains()[1]}
    assert "modified" in kinds
    with pytest.raises(CommandError, match="problem"):
        call_command("audit_verify")


def test_verify_detects_a_deleted_middle_row():
    events = [record("x.y.z", detail={"i": i}) for i in range(4)]
    _mutable()
    AuditEvent.objects.filter(pk=events[2].pk).delete()
    kinds = {p.kind for p in verify_chains()[1]}
    assert {"missing", "broken-link"} <= kinds


def test_verify_detects_a_deleted_last_row_through_the_head():
    events = [record("x.y.z", detail={"i": i}) for i in range(3)]
    _mutable()
    AuditEvent.objects.filter(pk=events[-1].pk).delete()
    assert "head-mismatch" in {p.kind for p in verify_chains()[1]}


def test_verify_detects_a_rewritten_hash_chain_through_anchors():
    record("x.y.z")
    record("x.y.z")
    with time_machine.travel(timezone.now() + timedelta(days=1)):
        anchors = anchor_finished_chains()
    assert len(anchors) == 1
    # An attacker deletes the last event and fixes up the head so the chain looks whole.
    _mutable()
    last = AuditEvent.objects.order_by("-seq").first()
    assert last is not None
    AuditEvent.objects.filter(pk=last.pk).delete()
    first = AuditEvent.objects.get()
    AuditChainHead.objects.update(last_seq=1, last_hash=first.hash)
    kinds = {p.kind for p in verify_chains()[1]}
    assert {"anchor-mismatch", "anchor-file"} <= kinds


def test_anchors_are_written_once_to_db_and_file():
    record("x.y.z", facility=1)
    record("x.y.z", facility=2)
    with time_machine.travel(timezone.now() + timedelta(days=1)):
        assert len(anchor_finished_chains()) == 2
        assert anchor_finished_chains() == []
    lines = anchor_file_path().read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert {json.loads(line)["facility_id"] for line in lines} == {1, 2}
    assert AuditAnchor.objects.count() == 2
    call_command("audit_anchor")  # nothing left to anchor for past days


def test_anchor_table_is_append_only_too():
    record("x.y.z")
    with time_machine.travel(timezone.now() + timedelta(days=1)):
        anchor_finished_chains()
    with pytest.raises(DatabaseError, match="append-only"), transaction.atomic():
        AuditAnchor.objects.update(event_count=0)


def test_production_migration_revokes_mutation_grants(settings):
    role = f"audit_app_{uuid.uuid4().hex[:8]}"
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE ROLE "{role}"')
        cursor.execute(
            f'GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON audit_auditevent, audit_auditanchor TO "{role}"'
        )
        settings.DJANGO_ENV = "prod"
        settings.DB_APP_ROLE = role
        revoke_migration.revoke(None, connection.schema_editor())
        for privilege in ("UPDATE", "DELETE", "TRUNCATE"):
            cursor.execute(
                "SELECT has_table_privilege(%s, 'audit_auditevent', %s)", [role, privilege]
            )
            assert cursor.fetchone()[0] is False
        cursor.execute("SELECT has_table_privilege(%s, 'audit_auditevent', 'INSERT')", [role])
        assert cursor.fetchone()[0] is True
        cursor.execute(f'REVOKE ALL ON audit_auditevent, audit_auditanchor FROM "{role}"')
        cursor.execute(f'DROP ROLE "{role}"')


def test_revocation_is_a_no_op_outside_production(settings):
    settings.DJANGO_ENV = "dev"
    settings.DB_APP_ROLE = "whoever"
    revoke_migration.revoke(None, None)  # would fail on the None schema editor if it ran


@pytest.mark.django_db(transaction=True)
def test_concurrent_appends_keep_the_chain_contiguous(settings, tmp_path_factory):
    settings.DATA_DIR = tmp_path_factory.mktemp("data")

    def worker(index):
        try:
            for step in range(5):
                record("x.y.concurrent", detail={"worker": index, "step": step}, facility=9)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    seqs = list(
        AuditEvent.objects.filter(facility_id=9).order_by("seq").values_list("seq", flat=True)
    )
    assert seqs == list(range(1, 21))
    assert verify_chains(facility_id=9)[1] == []
