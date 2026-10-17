"""Request signatures for Equity Bank's Jenga API (PAYMENTS.md §4; ADR-075).

Jenga signs each request with the merchant's RSA private key: the request's documented
fields are concatenated in a fixed order, signed with SHA-256 (PKCS#1 v1.5) and sent
Base64-encoded in the ``Signature`` header. Field orders below are the ones Jenga's guides
document (DECISIONS.md, Phase 3 findings):

    account balance           accountId + countryCode + date
    create payment link       expiryDate + amount + currency + amountOption + externalRef
    query transaction details ref

The private key lives outside the repository (``JENGA_PRIVATE_KEY_PATH``) and is read only
when signing. The same module verifies RSA signatures (KCB Buni IPNs, ``verify``).
"""

from __future__ import annotations

import base64
from decimal import Decimal
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def balance_message(account_id: str, country_code: str, on: str) -> str:
    return f"{account_id}{country_code}{on}"


def jenga_amount(amount: Decimal) -> str:
    """Amounts as Jenga's examples write them: ``400`` for a whole sum, ``400.5`` otherwise
    (GAP-JENGA-003: the exact formatting rule for decimals is not documented)."""
    text = format(amount.normalize(), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def payment_link_message(
    expiry_date: str, amount: Decimal, currency: str, amount_option: str, external_ref: str
) -> str:
    return f"{expiry_date}{jenga_amount(amount)}{currency}{amount_option}{external_ref}"


def transaction_details_message(ref: str) -> str:
    return ref


def load_private_key(path: str | Path) -> rsa.RSAPrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("The Jenga signing key must be an RSA private key.")
    return key


def load_public_key(path: str | Path) -> rsa.RSAPublicKey:
    key = serialization.load_pem_public_key(Path(path).read_bytes())
    if not isinstance(key, rsa.RSAPublicKey):
        raise ValueError("The verification key must be an RSA public key.")
    return key


def sign(message: str | bytes, key: rsa.RSAPrivateKey) -> str:
    data = message.encode() if isinstance(message, str) else message
    return base64.b64encode(key.sign(data, padding.PKCS1v15(), hashes.SHA256())).decode()


def verify(message: bytes, signature_b64: str, key: rsa.RSAPublicKey) -> bool:
    """SHA256withRSA (PKCS#1 v1.5) over ``message``; False on any malformed input."""
    try:
        signature = base64.b64decode(signature_b64.strip(), validate=True)
        key.verify(signature, message, padding.PKCS1v15(), hashes.SHA256())
    except (InvalidSignature, ValueError, TypeError):
        return False
    return True
