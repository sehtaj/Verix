"""Deterministic regression tests for the repository workflow through V0.8."""

from base64 import b64encode
from contextlib import nullcontext
from io import BytesIO
from pathlib import Path
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

from fastapi import HTTPException

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

import main as main_module
from services.github_service import (
    GitHubRepositoryService,
    RepositoryArchiveReference,
    RepositoryConfigurationFile,
    RepositoryGenerationSelection,
    RepositoryPaths,
    RepositoryTree,
    RepositoryTreeEntry,
)
from services.repository_preparer import PreparedRepository, PublicRepositoryPreparer
from services.docker_runner import (
    DEPENDENCY_INSTALL_TIMEOUT_SECONDS,
    GENERATED_TEST_DIRECTORY,
    GENERATED_TEST_FILENAME,
    REPOSITORY_TEST_TIMEOUT_SECONDS,
    DockerTestRunner,
    GeneratedTestsValidationError,
    RepositoryTestResults,
    TestExecutionResult as ExecutionResult,
)


REPOSITORY_URL = "https://github.com/example/sample"


def build_archive(
    files: dict[str, bytes], *, symlinks: dict[str, str] | None = None
) -> bytes:
    """Build a small in-memory GitHub-style tar archive for preparation tests."""
    archive_bytes = BytesIO()
    with tarfile.open(fileobj=archive_bytes, mode="w:gz") as archive:
        for path, content in files.items():
            member = tarfile.TarInfo(path)
            member.size = len(content)
            archive.addfile(member, BytesIO(content))

        for path, target in (symlinks or {}).items():
            member = tarfile.TarInfo(path)
            member.type = tarfile.SYMTYPE
            member.linkname = target
            archive.addfile(member)

    return archive_bytes.getvalue()


class GitHubRepositoryContextTests(unittest.TestCase):
    """Protect the consolidated repository evidence and planning behavior."""

    def test_likely_paths_exclude_test_package_initializers(self) -> None:
        service = GitHubRepositoryService()
        tree = RepositoryTree(
            entries=[
                RepositoryTreeEntry(path="src/sample.py", type="blob"),
                RepositoryTreeEntry(path="tests/__init__.py", type="blob"),
                RepositoryTreeEntry(path="tests/__main__.py", type="blob"),
                RepositoryTreeEntry(path="tests/test_sample.py", type="blob"),
            ],
            is_truncated=False,
        )

        paths = service._identify_likely_paths(tree)

        self.assertEqual(paths.source_paths, ["src/sample.py"])
        self.assertEqual(paths.test_paths, ["tests/test_sample.py"])

    def test_fetch_context_reuses_shared_evidence_and_builds_plan(self) -> None:
        service = GitHubRepositoryService()
        repository_data = {
            "name": "sample",
            "owner": {"login": "example"},
            "description": "A sample project",
            "language": "Python",
            "stargazers_count": 7,
            "html_url": REPOSITORY_URL,
            "default_branch": "main",
            "private": False,
        }
        tree = RepositoryTree(
            entries=[
                RepositoryTreeEntry(path="src/sample.py", type="blob"),
                RepositoryTreeEntry(path="tests/test_sample.py", type="blob"),
                RepositoryTreeEntry(path="examples/demo.py", type="blob"),
                RepositoryTreeEntry(path="requirements.txt", type="blob"),
            ],
            is_truncated=False,
            available_configuration_paths=("requirements.txt",),
        )
        configuration = [
            RepositoryConfigurationFile(
                path="requirements.txt", content="pytest==8.3.0\n"
            )
        ]

        with (
            patch.object(
                service, "_fetch_repository_data", return_value=repository_data
            ) as fetch_repository_data,
            patch.object(service, "_fetch_file_tree", return_value=tree) as fetch_tree,
            patch.object(
                service,
                "_fetch_configuration_files",
                return_value=configuration,
            ) as fetch_configuration,
        ):
            context = service.fetch_context(REPOSITORY_URL)

        fetch_repository_data.assert_called_once_with("example", "sample")
        fetch_tree.assert_called_once_with("example", "sample", repository_data)
        fetch_configuration.assert_called_once_with("example", "sample", tree)
        self.assertEqual(context.metadata.name, "sample")
        self.assertEqual(context.test_plan.source_paths, ["src/sample.py"])
        self.assertEqual(context.test_plan.test_paths, ["tests/test_sample.py"])
        self.assertEqual(context.test_plan.setup.project_tool, "pip")
        self.assertEqual(context.test_plan.setup.test_runner, "pytest")
        self.assertEqual(
            [step.action for step in context.test_plan.steps],
            ["prepare_environment", "run_existing_tests", "review_source_coverage"],
        )
        self.assertEqual(
            context.test_plan.steps[0].command,
            "pip install -r requirements.txt",
        )
        self.assertEqual(context.generation_selection.target_path, "src/sample.py")
        self.assertEqual(
            context.generation_selection.related_test_paths,
            ["tests/test_sample.py"],
        )
        self.assertEqual(
            context.generation_selection.configuration_paths,
            ["requirements.txt"],
        )

        context_service = Mock()
        context_service.fetch_context.return_value = context
        with patch.object(
            main_module, "github_repository_service", context_service
        ):
            response = main_module.get_repository_context(
                main_module.RepositoryRequest(url=REPOSITORY_URL)
            )

        self.assertEqual(
            response["generation_selection"],
            {
                "target_path": "src/sample.py",
                "related_test_paths": ["tests/test_sample.py"],
                "configuration_paths": ["requirements.txt"],
                "is_truncated": False,
            },
        )

    def test_generation_selection_is_focused_bounded_and_deterministic(self) -> None:
        paths = RepositoryPaths(
            source_paths=[
                "src/sample/__init__.py",
                "src/sample/alpha.py",
                "src/sample/orders.py",
                "app.py",
            ],
            test_paths=[
                "tests/test_zeta.py",
                "tests/test_orders.py",
                "tests/test_beta.py",
                "tests/test_alpha_behavior.py",
            ],
            is_truncated=True,
        )
        configuration_files = [
            RepositoryConfigurationFile("requirements.txt", "pytest\n"),
            RepositoryConfigurationFile("tox.ini", "[tox]\n"),
            RepositoryConfigurationFile("setup.py", "setup()\n"),
            RepositoryConfigurationFile("pyproject.toml", "[project]\n"),
            RepositoryConfigurationFile("setup.cfg", "[metadata]\n"),
        ]

        selection = GitHubRepositoryService._select_generation_context(
            paths, configuration_files
        )

        self.assertEqual(selection.target_path, "src/sample/orders.py")
        self.assertEqual(
            selection.related_test_paths,
            [
                "tests/test_orders.py",
                "tests/test_alpha_behavior.py",
                "tests/test_beta.py",
            ],
        )
        self.assertEqual(
            selection.configuration_paths,
            ["pyproject.toml", "setup.cfg", "tox.ini"],
        )
        self.assertTrue(selection.is_truncated)

    def test_generation_selection_handles_missing_source_candidates(self) -> None:
        selection = GitHubRepositoryService._select_generation_context(
            RepositoryPaths(
                source_paths=[],
                test_paths=["tests/test_orphan.py"],
                is_truncated=False,
            ),
            [RepositoryConfigurationFile("pyproject.toml", "[project]\n")],
        )

        self.assertIsNone(selection.target_path)
        self.assertEqual(selection.related_test_paths, [])
        self.assertEqual(selection.configuration_paths, ["pyproject.toml"])
        self.assertFalse(selection.is_truncated)

    def test_generation_context_fetches_only_selected_file_contents(self) -> None:
        service = GitHubRepositoryService()
        selection = RepositoryGenerationSelection(
            target_path="src/sample.py",
            related_test_paths=["tests/test_sample.py", "tests/test_other.py"],
            configuration_paths=["pyproject.toml"],
            is_truncated=False,
        )
        repository_context = SimpleNamespace(
            generation_selection=selection,
            configuration_files=[
                RepositoryConfigurationFile(
                    "pyproject.toml", "[tool.pytest.ini_options]\n"
                )
            ],
        )
        contents = {
            "src/sample.py": b"def add(a, b):\n    return a + b\n",
            "tests/test_sample.py": b"def test_add():\n    assert True\n",
            "tests/test_other.py": b"def test_other():\n    assert True\n",
        }

        def file_data(owner: str, repository: str, path: str) -> dict[str, object]:
            self.assertEqual((owner, repository), ("example", "sample"))
            content = contents[path]
            return {
                "type": "file",
                "encoding": "base64",
                "size": len(content),
                "content": b64encode(content).decode(),
            }

        with (
            patch.object(
                service, "fetch_context", return_value=repository_context
            ) as fetch_context,
            patch.object(service, "_fetch_file_data", side_effect=file_data) as fetch_file,
        ):
            context = service.fetch_generation_context(REPOSITORY_URL)

        fetch_context.assert_called_once_with(REPOSITORY_URL)
        self.assertEqual(
            [call.args[2] for call in fetch_file.call_args_list],
            ["src/sample.py", "tests/test_sample.py", "tests/test_other.py"],
        )
        self.assertEqual(context.source_file.path, "src/sample.py")
        self.assertIn("return a + b", context.source_file.content)
        self.assertEqual(
            [file.path for file in context.test_files],
            ["tests/test_sample.py", "tests/test_other.py"],
        )
        self.assertEqual(
            [file.path for file in context.configuration_files],
            ["pyproject.toml"],
        )
        self.assertEqual(context.skipped_paths, [])
        self.assertEqual(
            context.total_bytes,
            sum(len(content) for content in contents.values())
            + len("[tool.pytest.ini_options]\n".encode()),
        )

    def test_generation_context_skips_optional_files_that_exceed_limits(self) -> None:
        service = GitHubRepositoryService()
        selection = RepositoryGenerationSelection(
            target_path="src/sample.py",
            related_test_paths=[
                "tests/test_small.py",
                "tests/test_large.py",
                "tests/test_extra.py",
            ],
            configuration_paths=["pyproject.toml"],
            is_truncated=False,
        )
        repository_context = SimpleNamespace(
            generation_selection=selection,
            configuration_files=[
                RepositoryConfigurationFile("pyproject.toml", "cfg")
            ],
        )
        contents = {
            "src/sample.py": b"12345",
            "tests/test_small.py": b"123456",
            "tests/test_large.py": b"12345678901",
            "tests/test_extra.py": b"12345",
        }

        def file_data(owner: str, repository: str, path: str) -> dict[str, object]:
            content = contents[path]
            return {
                "type": "file",
                "encoding": "base64",
                "size": len(content),
                "content": b64encode(content).decode(),
            }

        with (
            patch.object(service, "fetch_context", return_value=repository_context),
            patch.object(service, "_fetch_file_data", side_effect=file_data),
            patch("services.github_service.MAX_GENERATION_FILE_BYTES", 10),
            patch("services.github_service.MAX_GENERATION_CONTEXT_BYTES", 15),
        ):
            context = service.fetch_generation_context(REPOSITORY_URL)

        self.assertEqual(
            [file.path for file in context.test_files],
            ["tests/test_small.py"],
        )
        self.assertEqual(
            context.skipped_paths,
            ["tests/test_large.py", "tests/test_extra.py"],
        )
        self.assertEqual(
            [file.path for file in context.configuration_files],
            ["pyproject.toml"],
        )
        self.assertEqual(context.total_bytes, 14)

    def test_generation_context_rejects_an_oversized_source_target(self) -> None:
        service = GitHubRepositoryService()
        repository_context = SimpleNamespace(
            generation_selection=RepositoryGenerationSelection(
                target_path="src/large.py",
                related_test_paths=[],
                configuration_paths=[],
                is_truncated=False,
            ),
            configuration_files=[],
        )
        large_content = b"x" * 11

        with (
            patch.object(service, "fetch_context", return_value=repository_context),
            patch.object(
                service,
                "_fetch_file_data",
                return_value={
                    "type": "file",
                    "encoding": "base64",
                    "size": len(large_content),
                    "content": b64encode(large_content).decode(),
                },
            ),
            patch("services.github_service.MAX_GENERATION_FILE_BYTES", 10),
        ):
            with self.assertRaisesRegex(ValueError, "source file is too large"):
                service.fetch_generation_context(REPOSITORY_URL)

    def test_configuration_fetch_decodes_only_present_allowlisted_files(self) -> None:
        service = GitHubRepositoryService()
        tree = RepositoryTree(
            entries=[],
            is_truncated=False,
            available_configuration_paths=("pyproject.toml",),
        )
        encoded_content = b64encode(b"[tool.pytest.ini_options]\n").decode()

        with patch.object(
            service,
            "_fetch_file_data",
            return_value={"content": encoded_content},
        ) as fetch_file:
            files = service._fetch_configuration_files("example", "sample", tree)

        fetch_file.assert_called_once_with("example", "sample", "pyproject.toml")
        self.assertEqual(
            files,
            [
                RepositoryConfigurationFile(
                    path="pyproject.toml",
                    content="[tool.pytest.ini_options]\n",
                )
            ],
        )


class RepositoryPreparationTests(unittest.TestCase):
    """Protect bounded extraction, validation, cleanup, and unsafe-path rejection."""

    @staticmethod
    def make_preparer(archive_data: bytes) -> PublicRepositoryPreparer:
        github_service = Mock(spec=GitHubRepositoryService)
        github_service.fetch_archive_reference.return_value = (
            RepositoryArchiveReference(
                owner="example",
                repository="sample",
                default_branch="main",
                url="https://api.github.test/archive",
            )
        )
        preparer = PublicRepositoryPreparer(github_service)
        preparer._download_archive = Mock(return_value=archive_data)
        return preparer

    def test_prepare_extracts_python_files_skips_links_and_cleans_up(self) -> None:
        files = {
            "sample-main/src/sample.py": b"VALUE = 1\n",
            "sample-main/tests/test_sample.py": b"def test_value(): pass\n",
        }
        archive_data = build_archive(
            files,
            symlinks={"sample-main/src/latest.py": "sample.py"},
        )
        preparer = self.make_preparer(archive_data)

        with preparer.prepare(REPOSITORY_URL) as prepared:
            prepared_path = prepared.path
            self.assertTrue((prepared_path / "src/sample.py").is_file())
            self.assertTrue((prepared_path / "tests/test_sample.py").is_file())
            self.assertFalse((prepared_path / "src/latest.py").exists())
            self.assertEqual(prepared.file_count, 2)
            self.assertEqual(prepared.total_bytes, sum(map(len, files.values())))
            self.assertEqual(prepared.skipped_entries, 1)

        self.assertFalse(prepared_path.exists())

    def test_prepare_rejects_parent_path_traversal(self) -> None:
        preparer = self.make_preparer(
            build_archive({"sample-main/../outside.py": b"unsafe = True\n"})
        )

        with self.assertRaisesRegex(ValueError, "unsafe path"):
            with preparer.prepare(REPOSITORY_URL):
                self.fail("Unsafe archives must never produce a repository.")

    def test_prepare_rejects_non_python_repository(self) -> None:
        preparer = self.make_preparer(
            build_archive({"sample-main/README.md": b"Not a Python project\n"})
        )

        with self.assertRaisesRegex(ValueError, "Python project"):
            with preparer.prepare(REPOSITORY_URL):
                self.fail("Non-Python archives must not be accepted.")


class RepositoryRunnerTests(unittest.TestCase):
    """Protect trusted command selection and repository container restrictions."""

    def test_generated_tests_are_added_only_to_disposable_workspace(self) -> None:
        runner = DockerTestRunner()
        generated_tests = "def test_generated():\n    assert True\n"

        with tempfile.TemporaryDirectory() as repository:
            repository_path = Path(repository)
            source_path = repository_path / "src/sample.py"
            source_path.parent.mkdir()
            source_path.write_text("VALUE = 1\n")

            with runner.repository_workspace(repository_path) as workspace_path:
                generated_path = runner.write_repository_generated_tests(
                    workspace_path,
                    "src/sample.py",
                    generated_tests,
                )
                disposable_workspace = workspace_path

                self.assertEqual(
                    generated_path,
                    workspace_path
                    / GENERATED_TEST_DIRECTORY
                    / GENERATED_TEST_FILENAME,
                )
                self.assertEqual(generated_path.read_text(), generated_tests)
                self.assertFalse(
                    (repository_path / GENERATED_TEST_DIRECTORY).exists()
                )

            self.assertFalse(disposable_workspace.exists())

    def test_generated_tests_do_not_overwrite_reserved_repository_path(self) -> None:
        runner = DockerTestRunner()

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            (workspace_path / "sample.py").write_text("VALUE = 1\n")
            generated_directory = workspace_path / GENERATED_TEST_DIRECTORY
            generated_directory.mkdir()
            existing_path = generated_directory / GENERATED_TEST_FILENAME
            existing_path.write_text("repository_owned = True\n")

            with self.assertRaisesRegex(ValueError, "reserved"):
                runner.write_repository_generated_tests(
                    workspace_path,
                    "sample.py",
                    "def test_generated():\n    assert True\n",
                )

            self.assertEqual(existing_path.read_text(), "repository_owned = True\n")

    def test_generated_tests_require_a_safe_existing_python_target(self) -> None:
        runner = DockerTestRunner()

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)

            for target_path in ("../outside.py", "missing.py", "README.md"):
                with self.subTest(target_path=target_path):
                    with self.assertRaisesRegex(ValueError, "target"):
                        runner.write_repository_generated_tests(
                            workspace_path,
                            target_path,
                            "def test_generated():\n    assert True\n",
                        )

    def test_generated_tests_must_be_valid_bounded_python(self) -> None:
        runner = DockerTestRunner()

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            (workspace_path / "sample.py").write_text("VALUE = 1\n")

            with self.assertRaisesRegex(ValueError, "valid Python"):
                runner.write_repository_generated_tests(
                    workspace_path,
                    "sample.py",
                    "def broken(:\n",
                )

            with (
                patch("services.docker_runner.MAX_GENERATED_TEST_BYTES", 10),
                self.assertRaisesRegex(ValueError, "allowed size"),
            ):
                runner.write_repository_generated_tests(
                    workspace_path,
                    "sample.py",
                    "def test_generated():\n    assert True\n",
                )

    def test_repository_test_sets_preserve_separate_results_and_order(self) -> None:
        runner = DockerTestRunner()
        existing_result = ExecutionResult(return_code=1, output="1 failed\n")
        generated_result = ExecutionResult(return_code=0, output="2 passed\n")

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            (workspace_path / "sample.py").write_text("VALUE = 1\n")

            def run_existing(
                received_workspace: Path, received_runner: str | None
            ) -> ExecutionResult:
                self.assertEqual(received_workspace, workspace_path)
                self.assertEqual(received_runner, "tox")
                self.assertFalse(
                    (workspace_path / GENERATED_TEST_DIRECTORY).exists()
                )
                return existing_result

            def run_generated(
                received_workspace: Path, received_runner: str | None
            ) -> ExecutionResult:
                self.assertEqual(received_workspace, workspace_path)
                self.assertEqual(received_runner, "tox")
                self.assertTrue(
                    (
                        workspace_path
                        / GENERATED_TEST_DIRECTORY
                        / GENERATED_TEST_FILENAME
                    ).is_file()
                )
                return generated_result

            with (
                patch.object(
                    runner,
                    "run_repository_tests",
                    side_effect=run_existing,
                ),
                patch.object(
                    runner,
                    "run_repository_generated_tests",
                    side_effect=run_generated,
                ),
            ):
                results = runner.run_repository_test_sets(
                    workspace_path,
                    "sample.py",
                    "def test_generated():\n    assert True\n",
                    "tox",
                )

        self.assertIsInstance(results, RepositoryTestResults)
        self.assertIs(results.existing, existing_result)
        self.assertIs(results.generated, generated_result)

    def test_generated_pytest_run_is_offline_read_only_and_focused(self) -> None:
        runner = DockerTestRunner()
        expected = ExecutionResult(return_code=0, output="2 passed\n")

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            (workspace_path / ".verix-venv").mkdir()
            generated_directory = workspace_path / GENERATED_TEST_DIRECTORY
            generated_directory.mkdir()
            (generated_directory / GENERATED_TEST_FILENAME).write_text(
                "def test_generated():\n    assert True\n"
            )

            with patch.object(
                runner, "run_repository_command", return_value=expected
            ) as run_command:
                result = runner.run_repository_generated_tests(
                    workspace_path, "pytest"
                )

        self.assertIs(result, expected)
        run_command.assert_called_once_with(
            workspace_path,
            [
                ".verix-venv/bin/python",
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "/workspace/.verix-generated-tests/test_verix_generated.py",
            ],
            allow_network=False,
            environment={"VIRTUAL_ENV": "/workspace/.verix-venv"},
            workspace_read_only=True,
            timeout_seconds=REPOSITORY_TEST_TIMEOUT_SECONDS,
        )

    def test_generated_tox_run_reuses_prepared_environment(self) -> None:
        runner = DockerTestRunner()
        expected = ExecutionResult(return_code=0, output="2 passed\n")
        listed_environments = ExecutionResult(
            return_code=0,
            output="pylint\npy313\ndocs\n",
        )

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            (workspace_path / ".verix-venv").mkdir()
            generated_directory = workspace_path / GENERATED_TEST_DIRECTORY
            generated_directory.mkdir()
            (generated_directory / GENERATED_TEST_FILENAME).write_text(
                "def test_generated():\n    assert True\n"
            )

            with patch.object(
                runner,
                "run_repository_command",
                side_effect=[listed_environments, expected],
            ) as run_command:
                result = runner.run_repository_generated_tests(
                    workspace_path, "tox"
                )

        self.assertIs(result, expected)
        self.assertEqual(
            run_command.call_args_list,
            [
                call(
                    workspace_path,
                    [
                        ".verix-venv/bin/python",
                        "-m",
                        "tox",
                        "list",
                        "--workdir",
                        "/tox-work",
                        "--no-desc",
                        "-d",
                    ],
                    allow_network=False,
                    environment={"VIRTUAL_ENV": "/workspace/.verix-venv"},
                    workspace_read_only=True,
                    timeout_seconds=REPOSITORY_TEST_TIMEOUT_SECONDS,
                ),
                call(
                    workspace_path,
                    [
                        ".verix-venv/bin/python",
                        "-m",
                        "tox",
                        "exec",
                        "--workdir",
                        "/tox-work",
                        "--skip-env-install",
                        "-e",
                        "py313",
                        "--",
                        "python",
                        "-m",
                        "pytest",
                        "-p",
                        "no:cacheprovider",
                        "/workspace/.verix-generated-tests/test_verix_generated.py",
                    ],
                    allow_network=False,
                    environment={"VIRTUAL_ENV": "/workspace/.verix-venv"},
                    workspace_read_only=True,
                    timeout_seconds=REPOSITORY_TEST_TIMEOUT_SECONDS,
                ),
            ],
        )

    def test_generated_tox_run_reports_missing_default_environment(self) -> None:
        runner = DockerTestRunner()

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            generated_directory = workspace_path / GENERATED_TEST_DIRECTORY
            generated_directory.mkdir()
            (generated_directory / GENERATED_TEST_FILENAME).write_text(
                "def test_generated():\n    assert True\n"
            )

            with patch.object(
                runner,
                "run_repository_command",
                return_value=ExecutionResult(return_code=0, output=""),
            ) as run_command:
                result = runner.run_repository_generated_tests(
                    workspace_path, "tox"
                )

        self.assertEqual(result.return_code, 2)
        self.assertIn("default test environment", result.output)
        run_command.assert_called_once()

    def test_generated_pytest_run_requires_the_verix_test_file(self) -> None:
        runner = DockerTestRunner()

        with tempfile.TemporaryDirectory() as workspace:
            with self.assertRaisesRegex(ValueError, "does not exist"):
                runner.run_repository_generated_tests(Path(workspace))

    def test_dependency_installation_uses_fixed_commands_and_network(self) -> None:
        runner = DockerTestRunner()
        successful_step = ExecutionResult(return_code=0, output="ok\n")

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            (workspace_path / "requirements.txt").write_text("pytest\n")

            with patch.object(
                runner,
                "run_repository_command",
                side_effect=[successful_step, successful_step],
            ) as run_command:
                result = runner.install_repository_dependencies(workspace_path)

        self.assertEqual(result.return_code, 0)
        self.assertFalse(result.skipped)
        self.assertIn("[Create isolated virtual environment]", result.output)
        self.assertIn("[Install dependencies from requirements.txt]", result.output)
        self.assertEqual(
            run_command.call_args_list[0],
            call(
                workspace_path,
                [
                    "python",
                    "-m",
                    "venv",
                    "--system-site-packages",
                    ".verix-venv",
                ],
            ),
        )
        dependency_call = run_command.call_args_list[1]
        self.assertEqual(
            dependency_call.args[1],
            [
                ".verix-venv/bin/python",
                "-m",
                "pip",
                "install",
                "--no-input",
                "--disable-pip-version-check",
                "--no-cache-dir",
                "-r",
                "requirements.txt",
            ],
        )
        self.assertTrue(dependency_call.kwargs["allow_network"])
        self.assertEqual(
            dependency_call.kwargs["timeout_seconds"],
            DEPENDENCY_INSTALL_TIMEOUT_SECONDS,
        )

    def test_dependency_failure_stops_before_later_install_steps(self) -> None:
        runner = DockerTestRunner()
        environment_created = ExecutionResult(return_code=0, output="created")
        installation_failed = ExecutionResult(return_code=1, output="failed")

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            (workspace_path / "requirements.txt").write_text("pytest\n")
            (workspace_path / "setup.py").write_text("from setuptools import setup\n")

            with patch.object(
                runner,
                "run_repository_command",
                side_effect=[environment_created, installation_failed],
            ) as run_command:
                result = runner.install_repository_dependencies(workspace_path)

        self.assertEqual(result.return_code, 1)
        self.assertIn("failed", result.output)
        self.assertEqual(run_command.call_count, 2)

    def test_no_dependencies_returns_skipped_installation(self) -> None:
        runner = DockerTestRunner()

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            with patch.object(runner, "run_repository_command") as run_command:
                result = runner.install_repository_dependencies(workspace_path)

        run_command.assert_not_called()
        self.assertEqual(result.return_code, 0)
        self.assertTrue(result.skipped)
        self.assertFalse(result.timed_out)
        self.assertIn("installation was skipped", result.output)

    def test_tox_environments_are_prepared_during_networked_installation(self) -> None:
        runner = DockerTestRunner()
        successful_step = ExecutionResult(return_code=0, output="ok\n")

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            (workspace_path / "tox.ini").write_text("[tox]\nenvlist = py\n")

            with patch.object(
                runner,
                "run_repository_command",
                side_effect=[successful_step, successful_step],
            ) as run_command:
                result = runner.install_repository_dependencies(workspace_path)

        self.assertEqual(result.return_code, 0)
        self.assertIn("[Prepare tox environments]", result.output)
        self.assertEqual(run_command.call_count, 2)
        tox_preparation_call = run_command.call_args_list[1]
        self.assertEqual(
            tox_preparation_call.args[1],
            [
                ".verix-venv/bin/python",
                "-m",
                "tox",
                "run",
                "--workdir",
                "/tox-work",
                "--notest",
            ],
        )
        self.assertTrue(tox_preparation_call.kwargs["allow_network"])
        self.assertEqual(
            tox_preparation_call.kwargs["timeout_seconds"],
            DEPENDENCY_INSTALL_TIMEOUT_SECONDS,
        )

    def test_reserved_environment_path_is_rejected(self) -> None:
        runner = DockerTestRunner()

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            (workspace_path / ".verix-venv").mkdir()

            with self.assertRaisesRegex(ValueError, "reserved .verix-venv"):
                runner.install_repository_dependencies(workspace_path)

    def test_reserved_tox_path_is_rejected(self) -> None:
        runner = DockerTestRunner()

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            (workspace_path / ".verix-tox").symlink_to("repository-owned-tox-data")

            with self.assertRaisesRegex(ValueError, "reserved .verix-tox"):
                runner.install_repository_dependencies(workspace_path)

    def test_pytest_run_is_offline_read_only_and_bounded(self) -> None:
        runner = DockerTestRunner()
        expected = ExecutionResult(return_code=0, output="3 passed\n")

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            with patch.object(
                runner, "run_repository_command", return_value=expected
            ) as run_command:
                result = runner.run_repository_tests(workspace_path, "pytest")

        self.assertIs(result, expected)
        run_command.assert_called_once_with(
            workspace_path,
            ["python", "-m", "pytest", "-p", "no:cacheprovider"],
            allow_network=False,
            environment={},
            workspace_read_only=True,
            timeout_seconds=REPOSITORY_TEST_TIMEOUT_SECONDS,
        )

    def test_tox_run_reuses_prepared_environment_offline_and_read_only(self) -> None:
        runner = DockerTestRunner()
        expected = ExecutionResult(return_code=0, output="tox passed\n")

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            (workspace_path / ".verix-venv").mkdir()
            with patch.object(
                runner, "run_repository_command", return_value=expected
            ) as run_command:
                result = runner.run_repository_tests(workspace_path, "tox")

        self.assertIs(result, expected)
        run_command.assert_called_once_with(
            workspace_path,
            [
                ".verix-venv/bin/python",
                "-m",
                "tox",
                "run",
                "--workdir",
                "/tox-work",
                "--skip-env-install",
            ],
            allow_network=False,
            environment={"VIRTUAL_ENV": "/workspace/.verix-venv"},
            workspace_read_only=True,
            timeout_seconds=REPOSITORY_TEST_TIMEOUT_SECONDS,
        )

    def test_repository_docker_command_keeps_security_limits(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            command = DockerTestRunner._repository_docker_command(
                workspace_path,
                "verix-test-container",
                ["python", "-m", "pytest"],
                allow_network=False,
                workspace_read_only=True,
            )

            workspace_mount = (
                f"type=bind,source={workspace_path.resolve()},"
                "target=/workspace,readonly"
            )
            tox_work_mount = (
                f"type=bind,source={(workspace_path / '.verix-tox').resolve()},"
                "target=/tox-work"
            )

        self.assertEqual(command[command.index("--network") + 1], "none")
        self.assertIn("--read-only", command)
        self.assertEqual(command[command.index("--cap-drop") + 1], "ALL")
        self.assertEqual(
            command[command.index("--security-opt") + 1],
            "no-new-privileges:true",
        )
        self.assertEqual(command[command.index("--pids-limit") + 1], "128")
        self.assertEqual(command[command.index("--memory") + 1], "512m")
        self.assertEqual(command[command.index("--cpus") + 1], "1")
        self.assertIn(workspace_mount, command)
        self.assertIn(tox_work_mount, command)
        self.assertEqual(command[command.index("--entrypoint") + 1], "python")
        self.assertEqual(command[-3:], ["verix-test-runner:dev", "-m", "pytest"])

    def test_missing_docker_executable_becomes_infrastructure_failure(self) -> None:
        with patch(
            "services.docker_runner.subprocess.run", side_effect=FileNotFoundError
        ):
            with self.assertRaisesRegex(RuntimeError, "Docker could not start"):
                DockerTestRunner._run_container(
                    ["docker", "run"],
                    "verix-test-container",
                    10,
                    "timed out",
                )

    def test_docker_startup_exit_code_becomes_infrastructure_failure(self) -> None:
        docker_result = SimpleNamespace(returncode=125, stdout="", stderr="failed")
        with patch(
            "services.docker_runner.subprocess.run", return_value=docker_result
        ):
            with self.assertRaisesRegex(RuntimeError, "Docker could not start"):
                DockerTestRunner._run_container(
                    ["docker", "run"],
                    "verix-test-container",
                    10,
                    "timed out",
                )


class RepositoryApiWorkflowTests(unittest.TestCase):
    """Protect API coordination and its public result shape."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.repository_path = Path(self.temporary_directory.name) / "prepared"
        self.workspace_path = Path(self.temporary_directory.name) / "workspace"
        self.repository_path.mkdir()
        self.workspace_path.mkdir()
        self.prepared = PreparedRepository(
            path=self.repository_path,
            file_count=4,
            total_bytes=128,
            skipped_entries=1,
        )

    def test_pasted_code_docker_failure_becomes_safe_502_response(self) -> None:
        llm = Mock()
        llm.generate_tests.return_value = "def test_generated(): pass\n"
        runner = Mock()
        runner.run_tests.side_effect = RuntimeError("sensitive Docker detail")

        with (
            patch.object(main_module, "llm_service", llm),
            patch.object(main_module, "test_runner", runner),
            self.assertRaises(HTTPException) as raised,
        ):
            main_module.generate_tests(
                main_module.GenerateTestsRequest(code="VALUE = 1")
            )

        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(
            raised.exception.detail,
            "Unable to execute generated tests. Please try again.",
        )

    def test_test_run_returns_separate_preparation_installation_and_execution(self) -> None:
        preparer = Mock()
        preparer.prepare.return_value = nullcontext(self.prepared)
        runner = Mock()
        runner.repository_workspace.return_value = nullcontext(self.workspace_path)
        runner.select_repository_test_runner.return_value = "pytest"
        runner.install_repository_dependencies.return_value = ExecutionResult(
            return_code=0,
            output="dependencies installed\n",
        )
        runner.run_repository_tests.return_value = ExecutionResult(
            return_code=1,
            output="1 failed\n",
        )

        with (
            patch.object(main_module, "repository_preparer", preparer),
            patch.object(main_module, "test_runner", runner),
        ):
            response = main_module.run_repository_test_suite(
                main_module.RepositoryRequest(url=REPOSITORY_URL)
            )

        self.assertEqual(
            response,
            {
                "preparation": {
                    "file_count": 4,
                    "total_bytes": 128,
                    "skipped_entries": 1,
                },
                "installation": {
                    "return_code": 0,
                    "output": "dependencies installed\n",
                    "timed_out": False,
                    "skipped": False,
                },
                "test_runner": "pytest",
                "execution": {
                    "return_code": 1,
                    "output": "1 failed\n",
                    "timed_out": False,
                    "skipped": False,
                },
            },
        )
        runner.run_repository_tests.assert_called_once_with(
            self.workspace_path, "pytest"
        )

    def test_repository_generation_returns_tests_and_separate_results(self) -> None:
        generation_context = SimpleNamespace(
            selection=SimpleNamespace(target_path="src/sample.py"),
            source_file=object(),
        )
        github_service = Mock()
        github_service.fetch_generation_context.return_value = generation_context
        llm = Mock()
        llm.generate_repository_tests.return_value = (
            "def test_generated():\n    assert True\n"
        )
        preparer = Mock()
        preparer.prepare.return_value = nullcontext(self.prepared)
        runner = Mock()
        runner.repository_workspace.return_value = nullcontext(self.workspace_path)
        runner.select_repository_test_runner.return_value = "pytest"
        runner.install_repository_dependencies.return_value = ExecutionResult(
            return_code=0,
            output="dependencies installed\n",
        )
        runner.run_repository_test_sets.return_value = RepositoryTestResults(
            existing=ExecutionResult(return_code=1, output="1 failed\n"),
            generated=ExecutionResult(return_code=0, output="2 passed\n"),
        )

        with (
            patch.object(main_module, "github_repository_service", github_service),
            patch.object(main_module, "llm_service", llm),
            patch.object(main_module, "repository_preparer", preparer),
            patch.object(main_module, "test_runner", runner),
        ):
            response = main_module.generate_repository_test_suite(
                main_module.RepositoryRequest(url=REPOSITORY_URL)
            )

        self.assertEqual(response["target_path"], "src/sample.py")
        self.assertEqual(
            response["generated_tests"],
            "def test_generated():\n    assert True\n",
        )
        self.assertEqual(response["existing_execution"]["return_code"], 1)
        self.assertEqual(response["existing_execution"]["output"], "1 failed\n")
        self.assertEqual(response["generated_execution"]["return_code"], 0)
        self.assertEqual(response["generated_execution"]["output"], "2 passed\n")
        github_service.fetch_generation_context.assert_called_once_with(
            REPOSITORY_URL
        )
        llm.generate_repository_tests.assert_called_once_with(generation_context)
        runner.run_repository_test_sets.assert_called_once_with(
            self.workspace_path,
            "src/sample.py",
            "def test_generated():\n    assert True\n",
            "pytest",
        )

    def test_invalid_generated_code_is_rejected_before_preparation(self) -> None:
        generation_context = SimpleNamespace(
            selection=SimpleNamespace(target_path="src/sample.py"),
            source_file=object(),
        )
        github_service = Mock()
        github_service.fetch_generation_context.return_value = generation_context
        llm = Mock()
        llm.generate_repository_tests.return_value = "def broken(:\n"
        preparer = Mock()
        runner = Mock()
        runner.validate_generated_tests.side_effect = GeneratedTestsValidationError(
            "Generated tests are not valid Python."
        )

        with (
            patch.object(main_module, "github_repository_service", github_service),
            patch.object(main_module, "llm_service", llm),
            patch.object(main_module, "repository_preparer", preparer),
            patch.object(main_module, "test_runner", runner),
            self.assertRaises(HTTPException) as raised,
        ):
            main_module.generate_repository_test_suite(
                main_module.RepositoryRequest(url=REPOSITORY_URL)
            )

        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(
            raised.exception.detail,
            "Gemini returned unusable generated tests. Please try again.",
        )
        preparer.prepare.assert_not_called()

    def test_repository_generation_skips_both_runs_after_install_failure(self) -> None:
        generation_context = SimpleNamespace(
            selection=SimpleNamespace(target_path="sample.py"),
            source_file=object(),
        )
        github_service = Mock()
        github_service.fetch_generation_context.return_value = generation_context
        llm = Mock()
        llm.generate_repository_tests.return_value = "def test_value(): pass\n"
        preparer = Mock()
        preparer.prepare.return_value = nullcontext(self.prepared)
        runner = Mock()
        runner.repository_workspace.return_value = nullcontext(self.workspace_path)
        runner.select_repository_test_runner.return_value = "tox"
        runner.install_repository_dependencies.return_value = ExecutionResult(
            return_code=2,
            output="installation failed\n",
        )

        with (
            patch.object(main_module, "github_repository_service", github_service),
            patch.object(main_module, "llm_service", llm),
            patch.object(main_module, "repository_preparer", preparer),
            patch.object(main_module, "test_runner", runner),
        ):
            response = main_module.generate_repository_test_suite(
                main_module.RepositoryRequest(url=REPOSITORY_URL)
            )

        self.assertTrue(response["existing_execution"]["skipped"])
        self.assertTrue(response["generated_execution"]["skipped"])
        self.assertIn(
            "dependency installation failed",
            response["existing_execution"]["output"],
        )
        self.assertIn(
            "dependency installation failed",
            response["generated_execution"]["output"],
        )
        runner.run_repository_test_sets.assert_not_called()

    def test_repository_generation_requires_the_llm_service(self) -> None:
        with patch.object(main_module, "llm_service", None):
            with self.assertRaises(HTTPException) as error:
                main_module.generate_repository_test_suite(
                    main_module.RepositoryRequest(url=REPOSITORY_URL)
                )

        self.assertEqual(error.exception.status_code, 503)

    def test_installation_failure_skips_repository_tests(self) -> None:
        preparer = Mock()
        preparer.prepare.return_value = nullcontext(self.prepared)
        runner = Mock()
        runner.repository_workspace.return_value = nullcontext(self.workspace_path)
        runner.select_repository_test_runner.return_value = "tox"
        runner.install_repository_dependencies.return_value = ExecutionResult(
            return_code=2,
            output="installation failed\n",
        )

        with (
            patch.object(main_module, "repository_preparer", preparer),
            patch.object(main_module, "test_runner", runner),
        ):
            response = main_module.run_repository_test_suite(
                main_module.RepositoryRequest(url=REPOSITORY_URL)
            )

        runner.run_repository_tests.assert_not_called()
        self.assertEqual(response["test_runner"], "tox")
        self.assertEqual(response["installation"]["return_code"], 2)
        self.assertEqual(
            response["execution"],
            {
                "return_code": None,
                "output": (
                    "Repository tests were not run because dependency "
                    "installation failed."
                ),
                "timed_out": False,
                "skipped": True,
            },
        )

    def test_invalid_repository_becomes_422_response_error(self) -> None:
        preparer = Mock()
        preparer.prepare.side_effect = ValueError("Repository is invalid.")

        with patch.object(main_module, "repository_preparer", preparer):
            with self.assertRaises(HTTPException) as raised:
                main_module.run_repository_test_suite(
                    main_module.RepositoryRequest(url=REPOSITORY_URL)
                )

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail, "Repository is invalid.")

    def test_infrastructure_failure_becomes_safe_502_response_error(self) -> None:
        preparer = Mock()
        preparer.prepare.side_effect = RuntimeError("sensitive internal detail")

        with patch.object(main_module, "repository_preparer", preparer):
            with self.assertRaises(HTTPException) as raised:
                main_module.run_repository_test_suite(
                    main_module.RepositoryRequest(url=REPOSITORY_URL)
                )

        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(
            raised.exception.detail,
            "Unable to prepare or test the repository. Please try again.",
        )


if __name__ == "__main__":
    unittest.main()
