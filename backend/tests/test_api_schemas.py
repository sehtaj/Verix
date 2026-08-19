"""Regression tests for safe repository request inputs."""

from pathlib import Path
import sys
import unittest

from pydantic import ValidationError


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from api.schemas import (
    RepositoryReferenceRequest,
    RepositoryRequest,
    RepositorySubdirectoryRequest,
    RepositoryTargetRequest,
)


REPOSITORY_URL = "https://github.com/example/sample"


class RepositoryTargetRequestTests(unittest.TestCase):
    """Protect the syntax and relationships of V0.10 targeting inputs."""

    def test_optional_targeting_inputs_default_to_current_behavior(self) -> None:
        request = RepositoryTargetRequest(url=REPOSITORY_URL)

        self.assertIsNone(request.reference)
        self.assertIsNone(request.subdirectory)
        self.assertIsNone(request.target_path)

    def test_accepts_branch_tag_commit_subdirectory_and_python_target(self) -> None:
        references = (
            "main",
            "feature/v0.10-targeting",
            "release-1.0",
            "a" * 40,
        )

        for reference in references:
            with self.subTest(reference=reference):
                request = RepositoryTargetRequest(
                    url=REPOSITORY_URL,
                    reference=reference,
                    subdirectory="backend/services",
                    target_path="backend/services/github_service.py",
                )

                self.assertEqual(request.reference, reference)
                self.assertEqual(request.subdirectory, "backend/services")
                self.assertEqual(
                    request.target_path, "backend/services/github_service.py"
                )

    def test_rejects_unsafe_git_references(self) -> None:
        invalid_references = (
            "",
            " main",
            "main ",
            "@",
            "-main",
            "/main",
            "main/",
            "feature//targeting",
            "feature..targeting",
            "main@{1}",
            ".hidden/main",
            "release.lock",
            "main~1",
            "main^",
            "main:other",
            "main?",
            "main*",
            "main[1]",
            "main\\other",
            "main\nother",
            "main\x7fother",
            "x" * 256,
        )

        for reference in invalid_references:
            with self.subTest(reference=reference):
                with self.assertRaises(ValidationError):
                    RepositoryTargetRequest(
                        url=REPOSITORY_URL,
                        reference=reference,
                    )

    def test_rejects_unsafe_repository_paths(self) -> None:
        invalid_paths = (
            "",
            " src",
            "src ",
            "/src",
            "./src",
            "src/",
            "src//package",
            "src/../package",
            "src/./package",
            "src\\package",
            "src/\x00package",
            "src/pack\nage",
            "src/pack\x7fage",
            "x" * 1025,
        )

        for subdirectory in invalid_paths:
            with self.subTest(subdirectory=subdirectory):
                with self.assertRaises(ValidationError):
                    RepositoryTargetRequest(
                        url=REPOSITORY_URL,
                        subdirectory=subdirectory,
                    )

    def test_rejects_non_python_or_unsafe_source_targets(self) -> None:
        invalid_targets = (
            "README.md",
            "/src/sample.py",
            "../sample.py",
            "src/../sample.py",
            "src\\sample.py",
            "src/sample.PY",
        )

        for target_path in invalid_targets:
            with self.subTest(target_path=target_path):
                with self.assertRaises(ValidationError):
                    RepositoryTargetRequest(
                        url=REPOSITORY_URL,
                        target_path=target_path,
                    )

    def test_source_target_must_be_inside_selected_subdirectory(self) -> None:
        with self.assertRaises(ValidationError):
            RepositoryTargetRequest(
                url=REPOSITORY_URL,
                subdirectory="backend",
                target_path="frontend/app.py",
            )

        with self.assertRaises(ValidationError):
            RepositoryTargetRequest(
                url=REPOSITORY_URL,
                subdirectory="backend",
                target_path="backendish/app.py",
            )

    def test_basic_repository_routes_reject_unhandled_targeting_fields(self) -> None:
        with self.assertRaises(ValidationError):
            RepositoryRequest(url=REPOSITORY_URL, reference="main")

        with self.assertRaises(ValidationError):
            RepositoryReferenceRequest(
                url=REPOSITORY_URL,
                reference="main",
                subdirectory="backend",
            )

        with self.assertRaises(ValidationError):
            RepositorySubdirectoryRequest(
                url=REPOSITORY_URL,
                reference="main",
                subdirectory="backend",
                target_path="backend/main.py",
            )


if __name__ == "__main__":
    unittest.main()
