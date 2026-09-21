import pytest

from shipping import STANDARD_SHIPPING_CENTS, shipping_fee


def test_order_below_threshold_pays_standard_shipping() -> None:
    assert shipping_fee(4_999) == STANDARD_SHIPPING_CENTS


def test_order_at_threshold_receives_free_shipping() -> None:
    assert shipping_fee(5_000) == 0


def test_negative_total_is_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        shipping_fee(-1)
