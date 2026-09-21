# Refund boundary example

## Selected target

`refunds.py`

## Expected-behavior source

The rules below are an explicit product specification. They are authoritative
for this example; behavior must not be inferred solely from the implementation.

`calculate_refund(amount_cents, days_since_purchase)` must:

- accept integers only; booleans are not valid integers for this contract;
- reject a non-positive amount or negative purchase age;
- return the full amount from day 0 through day 30, inclusive;
- return half the amount from day 31 through day 60, using integer division;
- return zero after day 60.

## Intentional known defect

The implementation uses `< 30` for the full-refund branch. A purchase exactly
30 days old incorrectly receives half of its amount.

## Expected evidence

- Existing suite: passes because it covers an ordinary recent purchase, an old
  purchase, and one invalid amount, but not day 30.
- Generated suite: should include a black-box day-30 boundary case and fail on
  the current implementation.
- Useful additional cases: days 0, 29, 31, 60, and 61; odd-cent half refunds;
  negative days; non-integer and boolean inputs.

## Assumptions and exclusions

Currency conversion, partial item returns, timestamps, time zones, concurrent
updates, and persistence are outside this example. An AI must label any
expectation beyond the explicit rules above as an assumption.
