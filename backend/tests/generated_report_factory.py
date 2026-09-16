"""Shared deterministic generated-test report fixtures."""

from models.generated_test_report import (
    BehaviorSource,
    BehaviorSourceKind,
    GeneratedTestReport,
)


def make_generated_test_report(
    tests: str = "def test_generated():\n    assert True\n",
) -> GeneratedTestReport:
    """Return compact report metadata suitable for unrelated workflow tests."""
    return GeneratedTestReport(
        tests=tests,
        sources=(
            BehaviorSource(
                kind=BehaviorSourceKind.SOURCE_CODE,
                path="src/sample.py",
                excerpt="def",
            ),
        ),
        assumptions=(),
        model="gemini-test",
    )
