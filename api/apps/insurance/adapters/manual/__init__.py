"""The manual payer: insurers with no integration (INSURANCE.md §8).

Eligibility is confirmed by phone or letter and recorded by staff; claims leave as a claim
pack (ZIP of PDFs and a CSV of lines, built by ``apps.insurance.claim_pack``) that the
claims officer sends; status changes and remittances are entered by hand (maker-checker).
"""

from .gateway import ManualGateway

__all__ = ["ManualGateway"]
