import pytest

from refunds import calculate_refund


def test_recent_purchase_receives_full_refund() -> None:
    assert calculate_refund(12_500, 10) == 12_500


def test_old_purchase_is_not_refundable() -> None:
    assert calculate_refund(12_500, 61) == 0


def test_non_positive_amount_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        calculate_refund(0, 10)
