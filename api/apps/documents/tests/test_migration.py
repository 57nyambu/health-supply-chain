import base64
import json
import os

import pytest
from django.core.management import CommandError, call_command

from apps.audit.models import AuditEvent
from apps.documents import migration, services, storage
from apps.documents.models import Document
from apps.patients.tests.factories import PatientFactory

from .conftest import BUCKET, pdf_bytes, upload_file

pytestmark = [pytest.mark.django_db, pytest.mark.req("KE-DHA-05")]


@pytest.fixture
def uploader(staff):
    return staff("clinical_officer")


@pytest.fixture
def stored(uploader, facility, settings):
    """Three documents on the local backend."""

    def make(count=3, backend="local"):
        settings.STORAGE_BACKEND = backend
        patient = PatientFactory.create(facility=facility)
        return [
            services.upload(
                actor=uploader,
                facility_id=facility.pk,
                content=upload_file(pdf_bytes(500 + i)),
                filename=f"f{i}.pdf",
                category="other",
                patient=patient,
            )
            for i in range(count)
        ]

    return make


def backends(documents):
    return {Document.objects.get(pk=d.pk).storage_backend for d in documents}


def readable(document):
    document.refresh_from_db()
    return b"".join(services.plaintext(document)).startswith(b"%PDF")


def test_dry_run_reports_and_moves_nothing(s3_store, stored):
    documents = stored()
    out = migration.migrate("local", "s3", dry_run=True)
    assert (out.selected, out.copied) == (3, 0)
    assert backends(documents) == {"local"}
    assert s3_store.list_objects_v2(Bucket=BUCKET).get("KeyCount", 0) == 0


def test_migrate_copies_verifies_and_flips_rows(s3_store, stored, local_store):
    documents = stored()
    call_command("storage_migrate", "--from", "local", "--to", "s3", "--verify", "--batch", "2")
    assert backends(documents) == {"s3"}
    for document in documents:
        head = s3_store.head_object(Bucket=BUCKET, Key=document.storage_key)
        assert head["ContentLength"] > 0
        assert (local_store / document.storage_key).exists()  # source kept until a purge run
        assert readable(document)
    batches = AuditEvent.objects.filter(action="documents.storage.migrated_batch")
    assert batches.count() == 2 and sum(e.detail["copied"] for e in batches) == 3


def test_an_interrupted_run_resumes(s3_store, stored, monkeypatch):
    documents = stored()
    real_write = storage.write
    calls = {"n": 0}

    def flaky(name, key, chunks):
        calls["n"] += 1
        if calls["n"] == 2:
            raise storage.StorageUnavailable()
        return real_write(name, key, chunks)

    monkeypatch.setattr(storage, "write", flaky)
    with pytest.raises(CommandError, match="failed 1"):
        call_command("storage_migrate", "--from", "local", "--to", "s3")
    assert sorted(Document.objects.values_list("storage_backend", flat=True)) == [
        "local",
        "s3",
        "s3",
    ]
    monkeypatch.setattr(storage, "write", real_write)
    report = migration.migrate("local", "s3")
    assert (report.selected, report.copied) == (1, 1)
    assert backends(documents) == {"s3"}


def test_partial_and_identical_destination_copies(s3_store, stored):
    first, second = stored(2)
    s3_store.put_object(Bucket=BUCKET, Key=first.storage_key, Body=b"half written")
    identical = b"".join(storage.read("local", second.storage_key))
    s3_store.put_object(Bucket=BUCKET, Key=second.storage_key, Body=identical)
    report = migration.migrate("local", "s3", verify=True)
    assert (report.copied, report.skipped, report.failed) == (1, 1, [])
    assert readable(first) and readable(second)


def test_a_corrupted_source_is_not_migrated(s3_store, stored, local_store):
    document, healthy = stored(2)
    path = local_store / document.storage_key
    path.write_bytes(b"x" + path.read_bytes()[1:])
    report = migration.migrate("local", "s3")
    assert report.failed == [
        (str(document.pk), "source object does not match its recorded checksum")
    ]
    assert Document.objects.get(pk=document.pk).storage_backend == "local"
    assert "Contents" not in s3_store.list_objects_v2(Bucket=BUCKET, Prefix=document.storage_key)
    assert Document.objects.get(pk=healthy.pk).storage_backend == "s3"


def test_purge_is_a_separate_run_after_verification(s3_store, stored, local_store):
    documents = stored()
    assert migration.purge_source("local", "s3").purged == 0  # nothing points at s3 yet
    migration.migrate("local", "s3")
    preview = migration.purge_source("local", "s3", dry_run=True)
    assert preview.purged == 3 and all((local_store / d.storage_key).exists() for d in documents)
    damaged = documents[0]
    s3_store.put_object(Bucket=BUCKET, Key=damaged.storage_key, Body=b"damaged")
    with pytest.raises(CommandError):
        call_command("storage_migrate", "--from", "local", "--to", "s3", "--purge-source")
    assert (local_store / damaged.storage_key).exists()  # kept: the destination did not verify
    assert not (local_store / documents[1].storage_key).exists()
    assert readable(documents[1]) and readable(documents[2])
    assert AuditEvent.objects.filter(action="documents.storage.purged_batch").exists()
    assert migration.purge_source("local", "s3").skipped == 2  # already purged


def test_migration_works_in_both_directions(s3_store, stored, settings):
    documents = stored(2, backend="s3")
    assert backends(documents) == {"s3"}
    call_command("storage_migrate", "--from", "s3", "--to", "local", "--verify")
    assert backends(documents) == {"local"}
    assert all(readable(d) for d in documents)
    call_command("storage_migrate", "--from", "s3", "--to", "local", "--purge-source")
    assert s3_store.list_objects_v2(Bucket=BUCKET).get("KeyCount", 0) == 0


def test_filters_and_argument_checks(s3_store, stored, facility):
    stored(2)
    assert migration.migrate("local", "s3", category="lab_report").selected == 0
    assert migration.migrate("local", "s3", facility=facility.pk + 999).selected == 0
    with pytest.raises(CommandError, match="differ"):
        call_command("storage_migrate", "--from", "local", "--to", "local")
    with pytest.raises(ValueError):
        migration.purge_source("local", "ftp")


def test_storage_verify_finds_missing_corrupted_and_undecryptable_objects(
    local_store, stored, settings, capsys
):
    settings.STORAGE_MASTER_KEYS = json.dumps({"k1": base64.b64encode(os.urandom(32)).decode()})
    corrupted, missing, healthy, rekeyed = stored(4)
    call_command("storage_verify")
    assert "4 of 4 objects intact" in capsys.readouterr().out
    path = local_store / corrupted.storage_key
    path.write_bytes(path.read_bytes()[:-1] + b"\x00")
    storage.delete("local", missing.storage_key)
    Document.objects.filter(pk=rekeyed.pk).update(enc_kid="retired")
    with pytest.raises(CommandError, match="3 failed"):
        call_command("storage_verify", "--backend", "local")
    errors = capsys.readouterr().err
    assert f"failed {corrupted.pk}: ciphertext checksum mismatch" in errors
    assert f"failed {missing.pk}: missing" in errors
    assert f"failed {rekeyed.pk}: decryption failed" in errors
    assert str(healthy.pk) not in errors
    sample = migration.verify(sample=2)
    assert sample.selected == 2
    assert AuditEvent.objects.filter(action="documents.storage.verified").count() == 3


def test_plaintext_checksum_is_checked_too(local_store, stored):
    (document,) = stored(1)
    Document.objects.filter(pk=document.pk).update(sha256_plain="0" * 64)
    document.refresh_from_db()
    assert migration.verify_document(document) == "plaintext checksum mismatch"


def test_storage_init_creates_the_dev_bucket(s3_store, settings, local_store):
    settings.S3_BUCKET = "afyasync-new"
    call_command("storage_init")
    assert s3_store.head_bucket(Bucket="afyasync-new")["ResponseMetadata"]["HTTPStatusCode"] == 200
    call_command("storage_init")  # idempotent
    assert local_store.is_dir()
    settings.DJANGO_ENV = "prod"
    with pytest.raises(CommandError, match="production"):
        call_command("storage_init")
