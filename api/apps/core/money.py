"""Money helpers (CLAUDE.md rule 5, DESIGN §10): KES as ``Decimal`` with 2 dp, ROUND_HALF_UP.

Never floats. API serializers output money as decimal strings (``"1500.00"``).
"""

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
MAX_DIGITS = 14
DECIMAL_PLACES = 2


def money(value: Any) -> Decimal:
    """``value`` as a 2 dp Decimal (ROUND_HALF_UP). Floats are refused: they are not exact."""
    if isinstance(value, float):
        raise TypeError("Money must not be a float; pass a Decimal, int or string.")
    if isinstance(value, Decimal):
        amount = value
    else:
        try:
            amount = Decimal(str(value).strip())
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError("Enter an amount in shillings, e.g. 1500.00.") from exc
    if not amount.is_finite():
        raise ValidationError("Enter an amount in shillings, e.g. 1500.00.")
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def multiply(amount: Any, quantity: Any) -> Decimal:
    """``amount * quantity`` rounded once at the end (quantities may be fractional)."""
    if isinstance(quantity, float):
        raise TypeError("Quantity must not be a float.")
    return money(money(amount) * Decimal(str(quantity)))


def total(amounts: Any) -> Decimal:
    return money(sum((money(a) for a in amounts), ZERO))


def whole_shillings_up(amount: Any) -> Decimal:
    """M-Pesa accepts whole shillings only (PAYMENTS.md §2): round a request *up* so the
    bill is covered; the excess becomes patient credit, never lost."""
    value = money(amount)
    return value.quantize(Decimal("1"), rounding=ROUND_CEILING).quantize(CENT)


def as_str(amount: Any) -> str:
    return f"{money(amount):.2f}"
