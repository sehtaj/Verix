"""Regression tests for repository test-command planning."""

from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from services.repository_test_commands import RepositoryTestCommandPlanner


class RepositoryTestCommandPlannerTests(unittest.TestCase):
    """Protect tox environment selection and focused command validation."""

    def test_tox_environment_prefers_python_style_default(self) -> None:
        environment = RepositoryTestCommandPlanner.select_tox_environment(
            "pylint\npy313\ndocs\n"
        )

        self.assertEqual(environment, "py313")

    def test_tox_environment_falls_back_to_first_safe_default(self) -> None:
        environment = RepositoryTestCommandPlanner.select_tox_environment(
            "lint\ndocs\n"
        )

        self.assertEqual(environment, "lint")

    def test_tox_environment_rejects_unsafe_reported_names(self) -> None:
        environment = RepositoryTestCommandPlanner.select_tox_environment(
            "py311; echo unsafe\n../py312\n"
        )

        self.assertIsNone(environment)

    def test_generated_tox_command_requires_selected_environment(self) -> None:
        with self.assertRaisesRegex(ValueError, "Tox environment is required"):
            RepositoryTestCommandPlanner.build_generated_test_command(
                ".verix-venv/bin/python",
                "tox",
            )

    def test_coverage_commands_are_trusted_and_target_focused(self) -> None:
        existing = RepositoryTestCommandPlanner.build_coverage_test_command(
            ".verix-venv/bin/python",
            "src/sample.py",
            generated_only=False,
        )
        generated = RepositoryTestCommandPlanner.build_coverage_test_command(
            ".verix-venv/bin/python",
            "src/sample.py",
            generated_only=True,
        )

        self.assertEqual(
            existing,
            [
                ".verix-venv/bin/python",
                "/opt/verix/coverage_runner.py",
                "--target",
                "/workspace/src/sample.py",
                "--",
                "-p",
                "no:cacheprovider",
            ],
        )
        self.assertEqual(
            generated[-1],
            "/workspace/.verix-generated-tests/test_verix_generated.py",
        )

    def test_coverage_command_rejects_paths_outside_the_repository(self) -> None:
        for target in ("../sample.py", "/tmp/sample.py", "README.md"):
            with self.subTest(target=target):
                with self.assertRaisesRegex(ValueError, "Coverage target"):
                    RepositoryTestCommandPlanner.build_coverage_test_command(
                        "python", target, generated_only=False
                    )
