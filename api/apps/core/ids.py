"""UUIDv7 identifiers (RFC 9562): time-ordered, unguessable, never sequential (DESIGN §17)."""

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    """48-bit Unix milliseconds, version 7, 74 random bits."""
    millis = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")
    value = (millis & ((1 << 48) - 1)) << 80
    value |= 0x7 << 76  # version
    value |= ((rand >> 62) & 0xFFF) << 64  # rand_a, 12 bits
    value |= 0b10 << 62  # RFC 9562 variant
    value |= rand & ((1 << 62) - 1)  # rand_b, 62 bits
    return uuid.UUID(int=value)
