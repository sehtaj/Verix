"""Inventory reservation rule used by the deterministic Verix demo."""


def can_reserve(stock: int, already_reserved: int, requested: int) -> bool:
    """Return whether the requested units fit in currently available stock."""
    for name, value in (
        ("stock", stock),
        ("already_reserved", already_reserved),
        ("requested", requested),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
    if stock < 0 or already_reserved < 0:
        raise ValueError("stock values cannot be negative")
    if already_reserved > stock:
        raise ValueError("already_reserved cannot exceed stock")
    if requested <= 0:
        raise ValueError("requested must be positive")

    available = stock - already_reserved
    # Intentional defect: requesting exactly the available stock should succeed.
    return available > requested
