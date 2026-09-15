"""Tests for running repository tests after disposable patch application."""

from contextlib import nullcontext
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from models.execution import RepositoryTestResults
from models.execution import TestExecutionResult as ExecutionResult
from models.fix_proposal import RepositoryApprovedFix
import main as main_module
from services.repository_preparer import PreparedRepository
from services.repository_workspace import GeneratedTestsValidationError
from workflows.repository_fix_application import AppliedRepositoryFixWorkspace
from workflows.repository_fix_application import RepositoryFixApplicationWorkflow
from workflows.repository_fix_verification import (
    RepositoryFixVerificationRun,
    RepositoryFixVerificationWorkflow,
)


class RepositoryFixVerificationWorkflowTests(unittest.TestCase):
    """Keep patched test execution inside the application workflow's workspace."""

    def test_runs_selected_repository_tests_after_disposable_application(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            application_workflow = Mock()
            application_workflow.apply.return_value = nullcontext(
                AppliedRepositoryFixWorkspace(
                    path=Path(workspace),
                    target_path="src/sample.py",
                )
            )
            test_runner = Mock()
            test_runner.select_repository_test_runner.return_value = "pytest"
            test_runner.install_repository_dependencies.return_value = (
                ExecutionResult(return_code=0, output="Installed dependencies.")
            )
            test_runner.run_repository_test_sets.return_value = RepositoryTestResults(
                existing=ExecutionResult(return_code=0, output="8 passed\n"),
                generated=ExecutionResult(return_code=0, output="1 passed\n"),
            )
            workflow = RepositoryFixVerificationWorkflow(
                application_workflow,
                test_runner,
            )
            approved_fix = self.make_approved_fix()

            result = workflow.run("https://github.com/example/sample", approved_fix)

            application_workflow.apply.assert_called_once_with(
                "https://github.com/example/sample",
                approved_fix,
            )
            test_runner.select_repository_test_runner.assert_called_once_with(
                Path(workspace)
            )
            test_runner.install_repository_dependencies.assert_called_once_with(
                Path(workspace)
            )
            test_runner.validate_generated_tests.assert_called_once_with(
                approved_fix.generated_tests
            )
            test_runner.run_repository_test_sets.assert_called_once_with(
                Path(workspace),
                "src/sample.py",
                approved_fix.generated_tests,
                "pytest",
            )
            self.assertEqual(result.test_runner, "pytest")
            self.assertEqual(result.existing_execution.return_code, 0)
            self.assertEqual(result.exposing_execution.return_code, 0)

    def test_skips_patched_tests_when_dependency_installation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            application_workflow = Mock()
            application_workflow.apply.return_value = nullcontext(
                AppliedRepositoryFixWorkspace(
                    path=Path(workspace),
                    target_path="src/sample.py",
                )
            )
            test_runner = Mock()
            test_runner.select_repository_test_runner.return_value = "pytest"
            test_runner.install_repository_dependencies.return_value = (
                ExecutionResult(
                    return_code=1,
                    output="Dependency installation failed.",
                )
            )
            workflow = RepositoryFixVerificationWorkflow(
                application_workflow,
                test_runner,
            )

            result = workflow.run(
                "https://github.com/example/sample",
                self.make_approved_fix(),
            )

            test_runner.run_repository_test_sets.assert_not_called()
            self.assertTrue(result.existing_execution.skipped)
            self.assertTrue(result.exposing_execution.skipped)
            self.assertIsNone(result.existing_execution.return_code)
            self.assertIsNone(result.exposing_execution.return_code)
            self.assertIn(
                "dependency installation failed",
                result.existing_execution.output,
            )

    def test_rejects_invalid_exposing_tests_before_repository_application(self) -> None:
        application_workflow = Mock()
        test_runner = Mock()
        test_runner.validate_generated_tests.side_effect = GeneratedTestsValidationError(
            "Generated tests are not valid Python."
        )
        workflow = RepositoryFixVerificationWorkflow(
            application_workflow,
            test_runner,
        )
        approved_fix = self.make_approved_fix()

        with self.assertRaisesRegex(
            GeneratedTestsValidationError,
            "not valid Python",
        ):
            workflow.run("https://github.com/example/sample", approved_fix)

        application_workflow.apply.assert_not_called()

    def test_runs_the_patched_copy_and_removes_it_after_execution(self) -> None:
        """Exercise application and verification together without Docker or GitHub."""
        source = "def add(a, b):\n    return a - b\n"
        patch_text = (
            "--- a/src/sample.py\n"
            "+++ b/src/sample.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def add(a, b):\n"
            "-    return a - b\n"
            "+    return a + b\n"
        )
        with tempfile.TemporaryDirectory() as repository_directory:
            project_path = Path(repository_directory)
            source_path = project_path / "src" / "sample.py"
            source_path.parent.mkdir()
            source_path.write_text(source, encoding="utf-8")
            preparer = Mock()
            preparer.prepare.return_value = nullcontext(
                PreparedRepository(
                    path=project_path,
                    file_count=1,
                    total_bytes=len(source.encode("utf-8")),
                    skipped_entries=0,
                )
            )
            test_runner = Mock()
            test_runner.select_repository_test_runner.return_value = "pytest"
            test_runner.install_repository_dependencies.return_value = ExecutionResult(
                return_code=0,
                output="Installed.",
            )
            observed_workspaces: list[Path] = []

            generated_tests = (
                "from src.sample import add\n\n"
                "def test_addition_contract():\n"
                "    assert add(2, 3) == 5\n"
            )

            def run_patched_tests(
                workspace: Path,
                target_path: str,
                tests: str,
                runner: str,
            ) -> RepositoryTestResults:
                observed_workspaces.append(workspace)
                self.assertEqual(runner, "pytest")
                self.assertEqual(target_path, "src/sample.py")
                self.assertEqual(tests, generated_tests)
                self.assertEqual(
                    (workspace / "src" / "sample.py").read_text(encoding="utf-8"),
                    "def add(a, b):\n    return a + b\n",
                )
                return RepositoryTestResults(
                    existing=ExecutionResult(return_code=0, output="8 passed\n"),
                    generated=ExecutionResult(return_code=0, output="1 passed\n"),
                )

            test_runner.run_repository_test_sets.side_effect = run_patched_tests
            workflow = RepositoryFixVerificationWorkflow(
                RepositoryFixApplicationWorkflow(preparer),
                test_runner,
            )

            result = workflow.run(
                "https://github.com/example/sample",
                RepositoryApprovedFix(
                    revision="a" * 40,
                    subdirectory=None,
                    target_path="src/sample.py",
                    patch=patch_text,
                    generated_tests=generated_tests,
                ),
            )

            self.assertEqual(result.existing_execution.return_code, 0)
            self.assertEqual(result.exposing_execution.return_code, 0)
            self.assertEqual(source_path.read_text(encoding="utf-8"), source)
            self.assertEqual(len(observed_workspaces), 1)
            self.assertFalse(observed_workspaces[0].exists())

    @staticmethod
    def make_approved_fix() -> RepositoryApprovedFix:
        return RepositoryApprovedFix(
            revision="a" * 40,
            subdirectory=None,
            target_path="src/sample.py",
            patch="--- a/src/sample.py\n+++ b/src/sample.py\n",
            generated_tests="def test_exposing_behavior():\n    assert True\n",
        )


class RepositoryFixVerificationApiTests(unittest.TestCase):
    """Protect the approval endpoint's temporary-only response contract."""

    def test_endpoint_returns_patched_test_results_without_github_changes(self) -> None:
        workflow = Mock()
        workflow.run.return_value = RepositoryFixVerificationRun(
            test_runner="pytest",
            installation=ExecutionResult(return_code=0, output="Installed."),
            existing_execution=ExecutionResult(return_code=0, output="8 passed\n"),
            exposing_execution=ExecutionResult(return_code=0, output="1 passed\n"),
        )
        request = main_module.RepositoryFixApplyRequest(
            url="https://github.com/example/sample",
            revision="a" * 40,
            target_path="src/sample.py",
            patch="--- a/src/sample.py\n+++ b/src/sample.py\n",
            generated_tests="def test_exposing_behavior():\n    assert True\n",
            approved=True,
        )

        with patch.object(
            main_module,
            "RepositoryFixVerificationWorkflow",
            return_value=workflow,
        ):
            response = main_module.verify_approved_repository_fix(request)

        approved_fix = workflow.run.call_args.args[1]
        self.assertEqual(workflow.run.call_args.args[0], request.url)
        self.assertEqual(approved_fix.revision, request.revision)
        self.assertTrue(response["approved"])
        self.assertTrue(response["applied_in_disposable_workspace"])
        self.assertFalse(response["github_changed"])
        self.assertEqual(approved_fix.generated_tests, request.generated_tests)
        self.assertEqual(response["existing_execution"]["return_code"], 0)
        self.assertEqual(response["exposing_execution"]["return_code"], 0)

    def test_endpoint_maps_execution_failures_to_safe_statuses(self) -> None:
        request = main_module.RepositoryFixApplyRequest(
            url="https://github.com/example/sample",
            revision="a" * 40,
            target_path="src/sample.py",
            patch="--- a/src/sample.py\n+++ b/src/sample.py\n",
            generated_tests="def test_exposing_behavior():\n    assert True\n",
            approved=True,
        )

        for failure, expected_status in ((ValueError("Patch no longer matches."), 422), (RuntimeError("docker detail"), 502)):
            with self.subTest(failure=type(failure).__name__):
                workflow = Mock()
                workflow.run.side_effect = failure
                with (
                    patch.object(
                        main_module,
                        "RepositoryFixVerificationWorkflow",
                        return_value=workflow,
                    ),
                    self.assertRaises(HTTPException) as raised,
                ):
                    main_module.verify_approved_repository_fix(request)

                self.assertEqual(raised.exception.status_code, expected_status)
                if expected_status == 502:
                    self.assertEqual(
                        raised.exception.detail,
                        "Unable to verify the approved repository fix. Please try again.",
                    )


if __name__ == "__main__":
    unittest.main()
