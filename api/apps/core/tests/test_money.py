"""core.money: Decimal KES, 2 dp, ROUND_HALF_UP, no floats (CLAUDE.md rule 5)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from hypothesis import given
from hypothesis import strategies as st

from apps.core.money import as_str, money, multiply, total, whole_shillings_up


def test_rounding_is_half_up_and_two_places():
    assert money("1.005") == Decimal("1.01")
    assert money("2.675") == Decimal("2.68")
    assert money(-1) == Decimal("-1.00")
    assert as_str("1500") == "1500.00"


def test_floats_and_garbage_are_refused():
    with pytest.raises(TypeError):
        money(0.1)
    with pytest.raises(TypeError):
        multiply("1.00", 0.5)
    for bad in ("abc", "NaN", "Infinity", ""):
        with pytest.raises(ValidationError):
            money(bad)


def test_multiply_rounds_once():
    assert multiply("33.33", 3) == Decimal("99.99")
    assert multiply("10.00", Decimal("0.333")) == Decimal("3.33")
    assert total(["0.10", "0.20", Decimal("0.30")]) == Decimal("0.60")


def test_mpesa_whole_shillings_round_up():
    assert whole_shillings_up("100.00") == Decimal("100.00")
    assert whole_shillings_up("100.01") == Decimal("101.00")
    assert whole_shillings_up("99.50") == Decimal("100.00")


@given(st.decimals(min_value=0, max_value=10**9, places=2, allow_nan=False, allow_infinity=False))
def test_whole_shilling_request_always_covers_the_bill(amount):
    rounded = whole_shillings_up(amount)
    assert rounded >= amount and rounded - amount < 1 and rounded == rounded.to_integral_value()
