"""Tests for the trusted coverage entrypoint copied into the Docker image."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from runner import coverage_runner


class CoverageRunnerTests(unittest.TestCase):
    """Protect the trusted command boundary and emitted metadata shape."""

    def test_runs_pytest_with_branch_measurement_and_emits_target_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            target = workspace_path / "sample.py"
            target.write_text("def choose(value):\n    return 1 if value else 0\n")
            calls: list[list[str]] = []

            def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append(command)
                if "json" in command:
                    output_path = Path(command[command.index("-o") + 1])
                    output_path.write_text(
                        json.dumps(
                            {
                                "files": {
                                    str(target): {
                                        "summary": {"num_branches": 2},
                                        "executed_branches": [[1, 2]],
                                    }
                                }
                            }
                        )
                    )
                    return subprocess.CompletedProcess(command, 0, "", "")
                return subprocess.CompletedProcess(command, 1, "1 failed\n", "")

            output = StringIO()
            with (
                patch.object(coverage_runner, "WORKSPACE", workspace_path),
                patch.object(coverage_runner.subprocess, "run", side_effect=run),
                patch.object(
                    sys,
                    "argv",
                    [
                        "coverage_runner.py",
                        "--target",
                        str(target),
                        "--",
                        "-p",
                        "no:cacheprovider",
                    ],
                ),
                redirect_stdout(output),
            ):
                return_code = coverage_runner.main()

        self.assertEqual(return_code, 1)
        self.assertIn("1 failed", output.getvalue())
        self.assertIn(
            'VERIX_BRANCH_COVERAGE={"target_path":"sample.py","total_branches":2,"executed_branches":[[1,2]]}',
            output.getvalue(),
        )
        self.assertIn("--rcfile=/dev/null", calls[0])
        self.assertIn("--branch", calls[0])
        self.assertIn(f"--source={target.parent}", calls[0])
        self.assertIn("--rcfile=/dev/null", calls[1])

