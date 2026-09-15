"""Shipping fee rules used by the deterministic Verix demo."""


STANDARD_SHIPPING_CENTS = 499
FREE_SHIPPING_THRESHOLD_CENTS = 5_000


def shipping_fee(order_total_cents: int) -> int:
    """Return the shipping fee for a non-negative order total."""
    if isinstance(order_total_cents, bool) or not isinstance(order_total_cents, int):
        raise TypeError("order_total_cents must be an integer")
    if order_total_cents < 0:
        raise ValueError("order_total_cents cannot be negative")

    # Intentional defect: an order exactly at the threshold should be free.
    if order_total_cents > FREE_SHIPPING_THRESHOLD_CENTS:
        return 0
    return STANDARD_SHIPPING_CENTS
