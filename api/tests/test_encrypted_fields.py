"""Secrets and raw payloads are encrypted at rest wherever they are stored (DESIGN §8.2, P1-DATA-01).

Any model field in our apps whose name says it holds a token, a raw payload or a message
body must use the encrypted field types — including models later phases add (payer consent
tokens, webhook inboxes).
"""

import pytest
from django.apps import apps

from apps.core.fields import EncryptedBinaryField, EncryptedTextField

SECRET_NAME_PARTS = ("token", "payload", "_body", "response_body", "request_body", "secret")
# Fields that hold hashes or digests (not recoverable), or legacy rows that are no longer used.
EXEMPT = {
    ("token_blacklist", "outstandingtoken", "token"),  # legacy JWTs, all blacklisted (P1-UAC-04)
    ("token_blacklist", "outstandingtoken", "jti"),
    ("token_blacklist", "blacklistedtoken", "token"),  # foreign key to the row above
    ("access", "approvalrequest", "payload"),  # IDs only; integrity via payload_hash
    ("access", "approvalrequest", "payload_hash"),
    # Domain events carry IDs and codes only; core.events.emit refuses personal-data keys.
    ("core", "outboxevent", "payload"),
}


def candidate_fields():
    for model in apps.get_models():
        for field in model._meta.concrete_fields:
            key = (model._meta.app_label, model._meta.model_name, field.name)
            name = field.name.lower()
            if key in EXEMPT or name.endswith(("_hash", "_index", "_hmac")):
                continue
            if any(part in name for part in SECRET_NAME_PARTS):
                yield key, field


@pytest.mark.req("KE-DPA-06")
def test_tokens_and_raw_payloads_use_encrypted_fields():
    plaintext = [
        ".".join(key)
        for key, field in candidate_fields()
        if not isinstance(field, EncryptedTextField | EncryptedBinaryField)
    ]
    assert plaintext == []


def test_the_guard_sees_the_exchange_log():
    names = {".".join(key) for key, _ in candidate_fields()}
    assert {
        "integrations.exchangelog.request_body",
        "integrations.exchangelog.response_body",
    } <= names
