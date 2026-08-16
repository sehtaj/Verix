"""Regression tests for repository API response presentation."""

from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from api.presenters import present_repository_context
from models.repository import (
    PythonProjectSetup,
    RepositoryConfigurationFile,
    RepositoryContext,
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
        )

        response = present_repository_context(context)

        self.assertEqual(
            response,
            {
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
