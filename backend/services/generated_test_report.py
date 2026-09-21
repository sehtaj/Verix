"""Parse and ground generated-test provenance in bounded repository context."""

import ast
import json

from models.generated_test_report import (
    BehaviorSource,
    BehaviorSourceKind,
    GeneratedTestCase,
    GeneratedTestReport,
    TestCaseCategory,
    TestDesignStrategy,
)
from models.repository import RepositoryGenerationContext


MAX_REPORT_LIST_ITEMS = 16
MAX_REPORT_CASES = 32
MAX_REPORT_TEXT_CHARACTERS = 1_000
MAX_SOURCE_EXCERPT_CHARACTERS = 500


class GeneratedTestReportValidationError(RuntimeError):
    """Keep a diagnostic reason without exposing it in the public error text."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__("Gemini returned an invalid generated-test report.")


def parse_generated_test_report(
    response: str,
    context: RepositoryGenerationContext,
    model: str,
) -> GeneratedTestReport:
    """Require generated tests with citations present in the supplied files."""
    try:
        payload = json.loads(response)
    except json.JSONDecodeError:
        raise GeneratedTestReportValidationError("response was not valid JSON") from None

    try:
        _require_keys(payload, {"tests", "sources", "assumptions", "cases"})
        tests = _bounded_text(payload["tests"], "tests", 128 * 1024)
        test_names = _pytest_function_names(tests)
        assumptions = _string_tuple(payload["assumptions"], "assumptions")
        source_contents = _source_contents(context)

        raw_sources = payload["sources"]
        if (
            not isinstance(raw_sources, list)
            or not 1 <= len(raw_sources) <= MAX_REPORT_LIST_ITEMS
        ):
            raise ValueError("sources must contain between 1 and 16 items")
        sources = tuple(
            _parse_source(item, source_contents) for item in raw_sources
        )

        raw_cases = payload["cases"]
        if (
            not isinstance(raw_cases, list)
            or not 1 <= len(raw_cases) <= MAX_REPORT_CASES
        ):
            raise ValueError("cases must contain between 1 and 32 items")
        cases = tuple(_parse_case(item) for item in raw_cases)
        classified_names = [case.test_name for case in cases]
        if (
            len(classified_names) != len(set(classified_names))
            or set(classified_names) != set(test_names)
        ):
            raise ValueError(
                "case names must match generated pytest function names exactly"
            )

        return GeneratedTestReport(
            tests=tests,
            sources=sources,
            assumptions=assumptions,
            cases=cases,
            model=model,
        )
    except (KeyError, TypeError, ValueError) as error:
        reason = str(error).strip() or "report fields violated validation rules"
        raise GeneratedTestReportValidationError(reason) from None


def _parse_source(
    value: object,
    source_contents: dict[tuple[BehaviorSourceKind, str], str],
) -> BehaviorSource:
    _require_keys(value, {"kind", "path", "excerpt"})
    kind = BehaviorSourceKind(value["kind"])
    path = _bounded_text(value["path"], "source path", 1_024)
    excerpt = _bounded_text(
        value["excerpt"], "source excerpt", MAX_SOURCE_EXCERPT_CHARACTERS
    )
    content = source_contents.get((kind, path))
    if content is None:
        raise ValueError("a cited source kind or path was not supplied")
    if excerpt not in content:
        raise ValueError("a cited excerpt was not copied exactly from its source")
    return BehaviorSource(kind=kind, path=path, excerpt=excerpt)


def _parse_case(value: object) -> GeneratedTestCase:
    _require_keys(
        value,
        {"test_name", "category", "strategy", "expected_behavior"},
    )
    test_name = _bounded_text(value["test_name"], "test name", 200)
    if not test_name.startswith("test_"):
        raise ValueError("every case name must start with test_")
    return GeneratedTestCase(
        test_name=test_name,
        category=TestCaseCategory(value["category"]),
        strategy=TestDesignStrategy(value["strategy"]),
        expected_behavior=_bounded_text(
            value["expected_behavior"],
            "expected behavior",
            MAX_REPORT_TEXT_CHARACTERS,
        ),
    )


def _source_contents(
    context: RepositoryGenerationContext,
) -> dict[tuple[BehaviorSourceKind, str], str]:
    contents: dict[tuple[BehaviorSourceKind, str], str] = {}
    if context.source_file is not None:
        contents[(BehaviorSourceKind.SOURCE_CODE, context.source_file.path)] = (
            context.source_file.content
        )
    for file in context.documentation_files:
        contents[(BehaviorSourceKind.DOCUMENTATION, file.path)] = file.content
    for file in context.test_files:
        contents[(BehaviorSourceKind.EXISTING_TEST, file.path)] = file.content
    for file in context.configuration_files:
        contents[(BehaviorSourceKind.CONFIGURATION, file.path)] = file.content
    return contents


def _pytest_function_names(tests: str) -> tuple[str, ...]:
    try:
        tree = ast.parse(tests)
    except SyntaxError:
        raise ValueError("generated tests were not valid Python") from None
    names = tuple(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    if not names or len(names) != len(set(names)):
        raise ValueError("generated tests need unique pytest function names")
    return names


def _string_tuple(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > MAX_REPORT_LIST_ITEMS:
        raise ValueError(f"{name} must be a list with at most 16 items")
    return tuple(
        _bounded_text(item, name, MAX_REPORT_TEXT_CHARACTERS) for item in value
    )


def _bounded_text(value: object, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(name)
    return value.strip()


def _require_keys(value: object, expected: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(
            "object keys must match exactly: " + ", ".join(sorted(expected))
        )
