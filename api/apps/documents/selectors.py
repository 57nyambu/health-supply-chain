"""Document lists shaped by chart access: categories above the user's level are left out,
sensitive items become placeholders unless the level is ``sensitive`` (P1-UAC-09)."""

from typing import Any

from apps.access import chart
from apps.core.sensitivity import redact
from apps.documents.models import Document
from apps.documents.services import CATEGORY_PERMISSION, visible_level


def summary(document: Document) -> dict[str, Any]:
    return {
        "id": str(document.pk),
        "kind": "document",
        "category": document.category,
        "sensitivity": document.sensitivity,
        "content_type": document.content_type,
        "size": document.size,
        "filename": document.original_filename,
        "created_at": document.created_at.isoformat(),
    }


def for_patient(patient: Any, decision: chart.ChartAccessDecision) -> list[dict[str, Any]]:
    documents = (
        Document.objects.filter(patient=patient, superseded_by__isnull=True)
        .exclude(category__in=list(CATEGORY_PERMISSION))
        .order_by("-created_at")
    )
    shown = [d for d in documents if decision.allows(visible_level(d.category))]
    return redact(shown, reveal=decision.sensitive, kind="document", serialize=summary)
