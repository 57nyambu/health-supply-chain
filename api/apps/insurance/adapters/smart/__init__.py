"""SMART (Smart Applications International / MediSmart) — INSURANCE.md §5; ADR-010.

There is no public API specification: access needs a provider integration agreement
(owner action, GAP-SMART-001). ``SMART_MODE=fake`` (default) runs ``FakeSmartGateway``;
``sandbox``/``live`` refuse to start until the spec and credentials exist. The real adapter
will be ``client.py`` (transport) + ``mapping.py`` (every field mapping), built only from
the vendor's spec or recorded sandbox traffic.
"""
