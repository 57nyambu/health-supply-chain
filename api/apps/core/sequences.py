"""Gap-free numbering per facility per year (MRN, invoices, receipts…; DESIGN §5).

``next_value`` takes a row lock on the counter, so concurrent callers queue and every
number is used exactly once — provided the caller's transaction commits. Call it
inside the transaction that creates the numbered record: a rollback releases the
number again, which is what keeps the series gap-free.
"""

from django.db import IntegrityError, transaction

from apps.core.models import Sequence


def next_value(*, facility_id: int, name: str, year: int) -> int:
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("next_value must run inside the transaction that uses the number")
    try:
        with transaction.atomic():
            Sequence.objects.get_or_create(facility_id=facility_id, name=name, year=year)
    except IntegrityError:
        pass  # created concurrently; lock it below
    counter = Sequence.objects.select_for_update().get(
        facility_id=facility_id, name=name, year=year
    )
    counter.last_value += 1
    counter.save(update_fields=["last_value"])
    return counter.last_value
