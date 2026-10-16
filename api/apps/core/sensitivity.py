"""Sensitive categories (DESIGN §7.7, P1-UAC-09).

Notes, diagnoses, results and documents inherit ``SensitiveRecord``. Items flagged with a
category are shown only at chart level ``sensitive`` (care team + ``clinical.record.read_sensitive``);
everyone else, break-glass included, sees a placeholder — in the chart, timelines and exports.
"""

from collections.abc import Callable, Iterable
from typing import Any

from django.db import models

PLACEHOLDER = "hidden: sensitive"


class SensitiveCategory(models.TextChoices):
    NORMAL = "normal", "Not sensitive"
    HIV = "hiv", "HIV and PrEP"
    MENTAL_HEALTH = "mental_health", "Mental health"
    SEXUAL_REPRODUCTIVE = "sexual_reproductive", "Sexual and reproductive health"
    GBV = "gbv", "Gender-based violence and post-rape care"
    SUBSTANCE_USE = "substance_use", "Substance use"
    GENETIC = "genetic", "Genetic results"


class SensitiveRecord(models.Model):
    sensitivity = models.CharField(
        max_length=30, choices=SensitiveCategory.choices, default=SensitiveCategory.NORMAL
    )

    class Meta:
        abstract = True

    @property
    def is_sensitive(self) -> bool:
        return self.sensitivity != SensitiveCategory.NORMAL


def placeholder(item: SensitiveRecord, kind: str) -> dict[str, Any]:
    """What users without sensitive access see instead of the item."""
    return {"id": str(item.pk), "kind": kind, "hidden": "sensitive", "label": PLACEHOLDER}


def redact[T: SensitiveRecord](
    items: Iterable[T], *, reveal: bool, kind: str, serialize: Callable[[T], dict[str, Any]]
) -> list[dict[str, Any]]:
    """Serialise items, replacing sensitive ones with a placeholder unless ``reveal``."""
    return [
        serialize(item) if reveal or not item.is_sensitive else placeholder(item, kind)
        for item in items
    ]
