# Verix deterministic Python examples

These small projects are controlled evidence for the recruiter-ready Verix
demo and LLM evaluation. Each project has an explicit behavior contract, one
intentional defect, a fixed target file, and a documented expected outcome.
They use only the Python standard library and pytest already present in the
Verix runner image.

| Example | Project folder | Existing-suite expectation | Intended evidence |
| --- | --- | --- | --- |
| Refund boundary | `examples/python/refund_boundary` | Pass | Generated boundary test should expose the day-30 defect |
| Shipping threshold | `examples/python/shipping_threshold` | Fail | Existing test should expose the exact free-shipping threshold defect |
| Inventory reservation | `examples/python/inventory_reservation` | No tests collected | Generated boundary test should expose the exact-stock defect |

The immutable GitHub revision for these folders is recorded separately after
the fixture commit exists. Do not use a branch name for a benchmark run.

These examples are intentionally narrow. They do not claim to represent every
Python project layout, dependency manager, framework, or failure mode.
