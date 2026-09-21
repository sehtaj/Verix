"""Refund amount rules used by the deterministic Verix demo."""


def calculate_refund(amount_cents: int, days_since_purchase: int) -> int:
    """Return the refundable amount for one completed purchase."""
    if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
        raise TypeError("amount_cents must be an integer")
    if isinstance(days_since_purchase, bool) or not isinstance(
        days_since_purchase, int
    ):
        raise TypeError("days_since_purchase must be an integer")
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    if days_since_purchase < 0:
        raise ValueError("days_since_purchase cannot be negative")

    # Intentional defect: the documented full-refund window includes day 30.
    if days_since_purchase < 30:
        return amount_cents
    if days_since_purchase <= 60:
        return amount_cents // 2
    return 0
