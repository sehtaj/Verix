"""Regression tests for repository API response presentation."""

from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from api.presenters import (
    present_repository_context,
    present_repository_generation_context,
)
from models.repository import (
    PythonProjectSetup,
    RepositoryConfigurationFile,
    RepositoryContext,
    RepositoryFileContent,
    RepositoryGenerationContext,
    RepositoryGenerationSelection,
    RepositoryMetadata,
    RepositoryTestPlan,
    RepositoryTestPlanStep,
    RepositoryTree,
    RepositoryTreeEntry,
)


class RepositoryApiPresenterTests(unittest.TestCase):
    """Protect the consolidated repository JSON contract."""

    def test_repository_context_preserves_existing_response_shape(self) -> None:
        context = RepositoryContext(
            metadata=RepositoryMetadata(
                name="sample",
                owner="example",
                description="Sample repository",
                language="Python",
                stars=7,
                url="https://github.com/example/sample",
            ),
            tree=RepositoryTree(
                entries=[RepositoryTreeEntry(path="src/sample.py", type="blob")],
                is_truncated=False,
            ),
            configuration_files=[
                RepositoryConfigurationFile(
                    path="requirements.txt", content="pytest\n"
                )
            ],
            test_plan=RepositoryTestPlan(
                setup=PythonProjectSetup(
                    is_python_project=True,
                    project_tool="pip",
                    test_runner="pytest",
                    configuration_files=["requirements.txt"],
                ),
                source_paths=["src/sample.py"],
                test_paths=["tests/test_sample.py"],
                steps=[
                    RepositoryTestPlanStep(
                        action="run_existing_tests",
                        description="Run the existing pytest test suite.",
                        command="pytest",
                    )
                ],
                is_truncated=False,
            ),
            generation_selection=RepositoryGenerationSelection(
                target_path="src/sample.py",
                related_test_paths=["tests/test_sample.py"],
                configuration_paths=["requirements.txt"],
                is_truncated=False,
            ),
            revision="a" * 40,
            subdirectory="packages/sample",
        )

        response = present_repository_context(context)

        self.assertEqual(
            response,
            {
                "revision": "a" * 40,
                "subdirectory": "packages/sample",
                "metadata": {
                    "name": "sample",
                    "owner": "example",
                    "description": "Sample repository",
                    "language": "Python",
                    "stars": 7,
                    "url": "https://github.com/example/sample",
                },
                "tree": {
                    "entries": [{"path": "src/sample.py", "type": "blob"}],
                    "is_truncated": False,
                },
                "configuration_files": [
                    {"path": "requirements.txt", "content": "pytest\n"}
                ],
                "test_plan": {
                    "setup": {
                        "is_python_project": True,
                        "project_tool": "pip",
                        "test_runner": "pytest",
                        "configuration_files": ["requirements.txt"],
                    },
                    "source_paths": ["src/sample.py"],
                    "test_paths": ["tests/test_sample.py"],
                    "steps": [
                        {
                            "action": "run_existing_tests",
                            "description": "Run the existing pytest test suite.",
                            "command": "pytest",
                        }
                    ],
                    "is_truncated": False,
                },
                "generation_selection": {
                    "target_path": "src/sample.py",
                    "related_test_paths": ["tests/test_sample.py"],
                    "configuration_paths": ["requirements.txt"],
                    "is_truncated": False,
                },
            },
        )

    def test_generation_context_preview_contains_exact_bounded_evidence(self) -> None:
        context = RepositoryGenerationContext(
            selection=RepositoryGenerationSelection(
                target_path="packages/sample/src/sample.py",
                related_test_paths=["packages/sample/tests/test_sample.py"],
                configuration_paths=["packages/sample/pyproject.toml"],
                is_truncated=False,
            ),
            source_file=RepositoryFileContent(
                path="packages/sample/src/sample.py",
                content="VALUE = 1\n",
                byte_count=10,
            ),
            test_files=[
                RepositoryFileContent(
                    path="packages/sample/tests/test_sample.py",
                    content="def test_value(): pass\n",
                    byte_count=23,
                )
            ],
            configuration_files=[
                RepositoryConfigurationFile(
                    path="packages/sample/pyproject.toml",
                    content="[project]\n",
                )
            ],
            skipped_paths=["packages/sample/tests/test_large.py"],
            total_bytes=43,
            revision="a" * 40,
            subdirectory="packages/sample",
        )

        response = present_repository_generation_context(context)

        self.assertEqual(response["revision"], "a" * 40)
        self.assertEqual(response["subdirectory"], "packages/sample")
        self.assertEqual(response["total_bytes"], 43)
        self.assertEqual(
            response["source_file"],
            {
                "path": "packages/sample/src/sample.py",
                "content": "VALUE = 1\n",
                "byte_count": 10,
            },
        )
        self.assertEqual(
            response["test_files"][0]["path"],
            "packages/sample/tests/test_sample.py",
        )
        self.assertEqual(
            response["configuration_files"],
            [
                {
                    "path": "packages/sample/pyproject.toml",
                    "content": "[project]\n",
                }
            ],
        )
        self.assertEqual(
            response["skipped_paths"],
            ["packages/sample/tests/test_large.py"],
        )
