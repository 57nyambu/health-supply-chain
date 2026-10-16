import base64
import json
import os

import pytest
from django.core.exceptions import FieldError, ImproperlyConfigured
from django.core.management import call_command
from django.db import connection

from apps.accounts.models import MfaDevice
from apps.core import crypto

KEY_A = base64.b64encode(b"a" * 32).decode()
KEY_B = base64.b64encode(b"b" * 32).decode()


@pytest.fixture(autouse=True)
def fresh_keys():
    crypto.reset_key_cache()
    yield
    crypto.reset_key_cache()


def use_keys(settings, *pairs):
    settings.FIELD_ENCRYPTION_KEYS = json.dumps(dict(pairs))
    crypto.reset_key_cache()


@pytest.mark.req("KE-DPA-06")
def test_round_trip_with_key_id(settings):
    use_keys(settings, ("k2", KEY_B), ("k1", KEY_A))
    token = crypto.encrypt("ID 00012345")
    assert token.startswith("v1.k2.")
    assert "00012345" not in token
    assert crypto.decrypt_text(token) == "ID 00012345"
    assert crypto.encrypt("same") != crypto.encrypt("same")  # random nonce


def test_tampering_and_unknown_keys_are_detected(settings):
    use_keys(settings, ("k1", KEY_A))
    token = crypto.encrypt("secret")
    head, kid, body = token.split(".")
    raw = bytearray(base64.urlsafe_b64decode(body))
    raw[-1] ^= 1
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(f"{head}.{kid}.{base64.urlsafe_b64encode(bytes(raw)).decode()}")
    with pytest.raises(crypto.DecryptionError, match="No key"):
        crypto.decrypt(f"v1.gone.{body}")
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt("not-a-token")


def test_aad_binds_the_ciphertext(settings):
    use_keys(settings, ("k1", KEY_A))
    token = crypto.encrypt("value", aad=b"patients.identifier:1")
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(token, aad=b"patients.identifier:2")


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "[]",
        "{}",
        json.dumps({"k": "not base64!"}),
        json.dumps({"k": base64.b64encode(b"x").decode()}),
    ],
)
def test_bad_key_configuration_is_refused(settings, raw):
    settings.FIELD_ENCRYPTION_KEYS = raw
    with pytest.raises(ImproperlyConfigured):
        crypto.keyring()


def test_production_never_falls_back_to_derived_keys(settings):
    settings.DJANGO_ENV = "prod"
    settings.FIELD_ENCRYPTION_KEYS = ""
    settings.FIELD_BLIND_INDEX_KEY = ""
    with pytest.raises(ImproperlyConfigured):
        crypto.keyring()
    with pytest.raises(ImproperlyConfigured):
        crypto.blind_index("x", purpose="p")


def test_blind_index_is_deterministic_normalised_and_purpose_bound(settings):
    settings.FIELD_BLIND_INDEX_KEY = "blind-key"
    a = crypto.blind_index(" a1234 567 ", purpose="patients.passport")
    assert a == crypto.blind_index("A1234567", purpose="patients.passport")
    assert a != crypto.blind_index("A1234567", purpose="patients.national_id")
    assert len(a) == 64 and "1234" not in a


@pytest.mark.django_db
def test_encrypted_fields_store_ciphertext_and_refuse_lookups(make_user):
    device = MfaDevice.objects.create(user=make_user(), secret="JBSWY3DPEHPK3PXP")
    with connection.cursor() as cursor:
        cursor.execute("SELECT secret FROM accounts_mfadevice WHERE id = %s", [device.pk])
        assert cursor.fetchone()[0].startswith("v1.")
    assert MfaDevice.objects.get(pk=device.pk).secret == "JBSWY3DPEHPK3PXP"
    with pytest.raises(FieldError, match="blind index"):
        MfaDevice.objects.filter(secret="JBSWY3DPEHPK3PXP").exists()
    assert MfaDevice.objects.filter(secret__isnull=False).exists()


@pytest.mark.django_db
def test_rotation_re_encrypts_in_batches_and_is_resumable(settings, make_user, capsys):
    use_keys(settings, ("k1", KEY_A))
    user = make_user()
    secrets_ = [base64.b32encode(os.urandom(10)).decode() for _ in range(7)]
    for secret in secrets_:
        MfaDevice.objects.create(user=user, secret=secret)
    use_keys(settings, ("k2", KEY_B), ("k1", KEY_A))
    call_command("rotate_field_keys", "--batch-size", "3")
    assert "7 value(s) re-encrypted" in capsys.readouterr().out
    with connection.cursor() as cursor:
        cursor.execute("SELECT secret FROM accounts_mfadevice")
        assert {row[0].split(".")[1] for row in cursor.fetchall()} == {"k2"}
    call_command("rotate_field_keys")  # nothing left: an interrupted run just resumes
    assert "0 value(s) re-encrypted" in capsys.readouterr().out
    use_keys(settings, ("k2", KEY_B))  # old key retired
    assert sorted(MfaDevice.objects.values_list("secret", flat=True)) == sorted(secrets_)


@pytest.mark.django_db
def test_rotation_never_overwrites_a_concurrent_write(settings, make_user):
    from apps.core.management.commands.rotate_field_keys import rotate_column

    use_keys(settings, ("k1", KEY_A))
    device = MfaDevice.objects.create(user=make_user(), secret="OLDSECRET")
    use_keys(settings, ("k2", KEY_B), ("k1", KEY_A))
    original = crypto.needs_rotation

    def write_meanwhile(token):
        MfaDevice.objects.filter(pk=device.pk).update(secret="NEWSECRET")
        return original(token)

    crypto.needs_rotation = write_meanwhile
    try:
        rotate_column(MfaDevice, MfaDevice._meta.get_field("secret"), 10)
    finally:
        crypto.needs_rotation = original
    assert MfaDevice.objects.get(pk=device.pk).secret == "NEWSECRET"
