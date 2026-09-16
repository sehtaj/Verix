"""Parse and ground generated-test provenance in bounded repository context."""

import ast
import json

from models.generated_test_report import (
    BehaviorSource,
    BehaviorSourceKind,
    GeneratedTestReport,
)
from models.repository import RepositoryGenerationContext


MAX_REPORT_LIST_ITEMS = 16
MAX_REPORT_TEXT_CHARACTERS = 1_000
MAX_SOURCE_EXCERPT_CHARACTERS = 500


def parse_generated_test_report(
    response: str,
    context: RepositoryGenerationContext,
    model: str,
) -> GeneratedTestReport:
    """Require generated tests with citations present in the supplied files."""
    try:
        payload = json.loads(response)
    except json.JSONDecodeError:
        raise RuntimeError("Gemini returned an invalid generated-test report.") from None

    try:
        _require_keys(payload, {"tests", "sources", "assumptions"})
        tests = _bounded_text(payload["tests"], "tests", 128 * 1024)
        _require_pytest_function(tests)
        assumptions = _string_tuple(payload["assumptions"], "assumptions")
        source_contents = _source_contents(context)

        raw_sources = payload["sources"]
        if (
            not isinstance(raw_sources, list)
            or not 1 <= len(raw_sources) <= MAX_REPORT_LIST_ITEMS
        ):
            raise ValueError
        sources = tuple(
            _parse_source(item, source_contents) for item in raw_sources
        )

        return GeneratedTestReport(
            tests=tests,
            sources=sources,
            assumptions=assumptions,
            model=model,
        )
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("Gemini returned an invalid generated-test report.") from None


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
    if content is None or excerpt not in content:
        raise ValueError
    return BehaviorSource(kind=kind, path=path, excerpt=excerpt)


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


def _require_pytest_function(tests: str) -> None:
    try:
        tree = ast.parse(tests)
    except SyntaxError:
        raise ValueError from None
    if not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(tree)
    ):
        raise ValueError


def _string_tuple(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > MAX_REPORT_LIST_ITEMS:
        raise ValueError
    return tuple(
        _bounded_text(item, name, MAX_REPORT_TEXT_CHARACTERS) for item in value
    )


def _bounded_text(value: object, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(name)
    return value.strip()


def _require_keys(value: object, expected: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError
