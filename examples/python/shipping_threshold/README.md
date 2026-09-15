# Shipping threshold example

## Selected target

`shipping.py`

## Expected-behavior source

The following explicit product specification is authoritative:

- non-negative integer order totals below 5,000 cents pay 499 cents shipping;
- order totals of 5,000 cents or more receive free shipping;
- negative totals raise `ValueError`;
- non-integer values and booleans raise `TypeError`.

## Intentional known defect

The implementation checks `> 5_000` instead of `>= 5_000`. The existing test
for an order exactly at the threshold therefore fails deterministically.

## Expected evidence

- Existing suite: fails only at the exact threshold test.
- Generated suite: should cover ordinary totals, the 4,999/5,000/5,001 boundary,
  negative input, and invalid types without replacing the existing failure.
- Investigation: should cite the returned assertion evidence rather than invent
  an unrelated cause.

## Assumptions and exclusions

Taxes, discounts, currencies, shipment destinations, cart contents, and
floating-point inputs are outside this contract. An AI must mark any behavior
for those concerns as assumed or untested.
