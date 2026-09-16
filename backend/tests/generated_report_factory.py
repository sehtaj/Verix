"""Shared deterministic generated-test report fixtures."""

from models.generated_test_report import (
    BehaviorSource,
    BehaviorSourceKind,
    GeneratedTestCase,
    GeneratedTestReport,
    TestCaseCategory,
    TestDesignStrategy,
)


def make_generated_test_report(
    tests: str = "def test_generated():\n    assert True\n",
) -> GeneratedTestReport:
    """Return compact report metadata suitable for unrelated workflow tests."""
    test_name = next(
        (
            line.split("(", 1)[0].removeprefix("def ")
            for line in tests.splitlines()
            if line.startswith("def test_")
        ),
        "test_generated",
    )
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
        cases=(
            GeneratedTestCase(
                test_name=test_name,
                category=TestCaseCategory.NORMAL,
                strategy=TestDesignStrategy.BLACK_BOX,
                expected_behavior="The selected behavior matches its contract.",
            ),
        ),
        model="gemini-test",
    )
