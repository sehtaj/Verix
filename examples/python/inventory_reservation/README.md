# Inventory reservation example

## Selected target

`inventory.py`

## Expected-behavior source

This explicit product specification is authoritative:

- `stock`, `already_reserved`, and `requested` are integers, excluding booleans;
- stock values cannot be negative and reserved units cannot exceed stock;
- requested units must be positive;
- a reservation succeeds when requested units are less than or equal to the
  currently available units (`stock - already_reserved`).

## Intentional known defect

The implementation uses strict `>` comparison. A request exactly equal to the
available units incorrectly returns `False`.

## Expected evidence

- Existing suite: pytest reports no tests collected.
- Generated suite: should establish normal success and rejection paths, test
  the exact-availability boundary, and validate documented exceptions.
- A useful gray-box test sees the risky comparison but asserts only through the
  public `can_reserve` function.

## Assumptions and exclusions

Concurrent reservations, persistence, inventory identifiers, replenishment,
and integer overflow are outside this example. An AI must not silently turn
those topics into asserted requirements.
