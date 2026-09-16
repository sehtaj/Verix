"""Deterministic summary of what one repository run did and did not prove."""

from dataclasses import dataclass
from enum import StrEnum

from models.generated_test_report import BehaviorSource


class EvidenceAssessment(StrEnum):
    """Top-level interpretation derived only from recorded evidence."""

    OBSERVED_FAILURES = "observed_failures"
    INCOMPLETE = "incomplete"
    NO_OBSERVED_FAILURES = "no_observed_failures"


@dataclass(frozen=True)
class EvidenceSummary:
    """Bounded factual buckets shown without claiming correctness."""

    assessment: EvidenceAssessment
    passed: tuple[str, ...]
    failed: tuple[str, ...]
    assumed: tuple[str, ...]
    untested: tuple[str, ...]
    behavior_sources: tuple[BehaviorSource, ...]

