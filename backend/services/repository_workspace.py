"""Manage disposable repository copies and generated test files."""

import ast
from contextlib import contextmanager
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Iterator


GENERATED_TEST_DIRECTORY = ".verix-generated-tests"
GENERATED_TEST_FILENAME = "test_verix_generated.py"
MAX_GENERATED_TEST_BYTES = 128 * 1024


class GeneratedTestsValidationError(ValueError):
    """Raised when LLM output cannot safely become a Python test module."""


class RepositoryWorkspaceManager:
    """Create writable repository copies and safely add generated tests."""

    @contextmanager
    def create(self, repository_path: Path) -> Iterator[Path]:
        """Yield an isolated writable copy of a repository, then remove it."""
        if not repository_path.is_dir():
            raise ValueError("Prepared repository directory does not exist.")

        with tempfile.TemporaryDirectory(
            prefix="verix-repository-runner-"
        ) as workspace:
            workspace_path = Path(workspace) / "repository"
            shutil.copytree(repository_path, workspace_path, symlinks=True)
            self._make_writable(workspace_path)
            yield workspace_path

    def write_generated_tests(
        self,
        workspace_path: Path,
        target_path: str,
        generated_tests: str,
        *,
        maximum_bytes: int = MAX_GENERATED_TEST_BYTES,
    ) -> Path:
        """Safely add one generated pytest module to a repository copy."""
        if not workspace_path.is_dir():
            raise ValueError("Repository workspace directory does not exist.")

        relative_target = PurePosixPath(target_path)
        if (
            not target_path
            or "\\" in target_path
            or relative_target.is_absolute()
            or ".." in relative_target.parts
            or relative_target.suffix != ".py"
        ):
            raise ValueError("Repository generation target path is invalid.")

        target_file = workspace_path.joinpath(*relative_target.parts)
        current_path = workspace_path
        for part in relative_target.parts:
            current_path /= part
            if current_path.is_symlink():
                raise ValueError("Repository generation target cannot use symlinks.")
        if not target_file.is_file():
            raise ValueError("Repository generation target does not exist.")

        self.validate_generated_tests(generated_tests, maximum_bytes=maximum_bytes)

        generated_directory = workspace_path / GENERATED_TEST_DIRECTORY
        if generated_directory.exists() or generated_directory.is_symlink():
            raise ValueError(
                f"Repository contains the reserved {GENERATED_TEST_DIRECTORY} path."
            )

        generated_directory.mkdir(mode=0o755)
        generated_test_path = generated_directory / GENERATED_TEST_FILENAME
        with generated_test_path.open("x", encoding="utf-8") as generated_file:
            generated_file.write(generated_tests)
        os.chmod(generated_test_path, 0o644)
        return generated_test_path

    @staticmethod
    def validate_generated_tests(
        generated_tests: str,
        *,
        maximum_bytes: int = MAX_GENERATED_TEST_BYTES,
    ) -> None:
        """Reject unusable generated code before setup or execution."""
        if not isinstance(generated_tests, str) or not generated_tests.strip():
            raise GeneratedTestsValidationError("Generated tests cannot be empty.")
        if "\x00" in generated_tests:
            raise GeneratedTestsValidationError(
                "Generated tests contain invalid characters."
            )
        if len(generated_tests.encode("utf-8")) > maximum_bytes:
            raise GeneratedTestsValidationError(
                "Generated tests exceed the allowed size."
            )
        try:
            ast.parse(generated_tests)
        except SyntaxError:
            raise GeneratedTestsValidationError(
                "Generated tests are not valid Python."
            ) from None

    @staticmethod
    def _make_writable(workspace_path: Path) -> None:
        """Allow the non-root container user to modify only the temporary copy."""
        os.chmod(workspace_path, 0o777)
        for path in workspace_path.rglob("*"):
            if path.is_symlink():
                continue
            if path.is_dir():
                os.chmod(path, 0o777)
                continue

            executable = bool(path.stat().st_mode & 0o111)
            os.chmod(path, 0o777 if executable else 0o666)
