"""Regression tests for hosted E2B execution without external API calls."""

from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from services.e2b_runner import E2BTestRunner


def command_result(
    exit_code: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


class FakeFiles:
    def __init__(self) -> None:
        self.writes: list[tuple[str, object, str | None]] = []

    def write(self, path: str, data: object, user: str | None = None) -> None:
        self.writes.append((path, data, user))


class FakeCommands:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.results: list[SimpleNamespace] = []

    def run(self, command: str, **kwargs: object) -> SimpleNamespace:
        self.calls.append({"command": command, **kwargs})
        if self.results:
            return self.results.pop(0)
        return command_result()


class FakeSandbox:
    def __init__(self) -> None:
        self.files = FakeFiles()
        self.commands = FakeCommands()
        self.network_updates: list[dict[str, object]] = []
        self.killed = False

    def update_network(self, network: dict[str, object]) -> None:
        self.network_updates.append(network)

    def kill(self) -> None:
        self.killed = True


class E2BTestRunnerTests(unittest.TestCase):
    """Keep cloud lifecycle and network boundaries deterministic."""

    def test_workspace_uploads_locks_network_and_always_kills_sandbox(self) -> None:
        sandbox = FakeSandbox()
        created: list[dict[str, object]] = []

        def factory(template: str, **kwargs: object) -> FakeSandbox:
            created.append({"template": template, **kwargs})
            return sandbox

        runner = E2BTestRunner(sandbox_factory=factory)
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "sample.py").write_text("value = 1\n")
            with runner.execution_workspace(workspace):
                sandbox.commands.results.extend(
                    [
                        command_result(),
                        command_result(
                            exit_code=1,
                            stdout="failed\n",
                            stderr="detail\n",
                        ),
                    ]
                )
                result = runner.run_repository_command(
                    workspace,
                    ["python", "-c", "print('safe value')"],
                    allow_network=False,
                    workspace_read_only=True,
                )
                self.assertFalse(sandbox.killed)

        self.assertEqual(created[0]["template"], "verix-python-runner")
        self.assertTrue(created[0]["allow_internet_access"])
        self.assertEqual(sandbox.files.writes[0][0], "/tmp/verix-workspace.tar.gz")
        self.assertEqual(
            sandbox.network_updates,
            [{"deny_out": ["0.0.0.0/0", "::/0"]}],
        )
        self.assertEqual(result.return_code, 1)
        self.assertEqual(result.output, "failed\ndetail\n")
        self.assertEqual(
            sandbox.commands.calls[-2]["command"],
            "chmod -R a-w /workspace",
        )
        self.assertIn(
            "python -c 'print('\"'\"'safe value'\"'\"')'",
            sandbox.commands.calls[-1]["command"],
        )
        self.assertTrue(sandbox.killed)

    def test_dependency_install_keeps_network_until_tests_begin(self) -> None:
        sandbox = FakeSandbox()
        runner = E2BTestRunner(sandbox_factory=lambda *args, **kwargs: sandbox)
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "requirements.txt").write_text("pytest==9.1.1\n")
            with runner.execution_workspace(workspace):
                installation = runner.install_repository_dependencies(workspace)
                self.assertEqual(installation.return_code, 0)
                self.assertEqual(sandbox.network_updates, [])
                python, environment = runner._repository_python_environment(workspace)
                self.assertEqual(python, ".verix-venv/bin/python")
                self.assertEqual(
                    environment,
                    {"VIRTUAL_ENV": "/workspace/.verix-venv"},
                )
                runner.run_repository_command(
                    workspace,
                    [python, "-m", "pytest"],
                    allow_network=False,
                    environment=environment,
                    workspace_read_only=True,
                )

        self.assertEqual(
            sandbox.network_updates,
            [{"deny_out": ["0.0.0.0/0", "::/0"]}],
        )

    def test_generated_tests_are_written_to_the_active_sandbox(self) -> None:
        sandbox = FakeSandbox()
        runner = E2BTestRunner(sandbox_factory=lambda *args, **kwargs: sandbox)
        tests = "def test_value():\n    assert True\n"
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "sample.py").write_text("value = 1\n")
            with runner.execution_workspace(workspace):
                runner.write_repository_generated_tests(
                    workspace,
                    "sample.py",
                    tests,
                )

        self.assertEqual(
            sandbox.files.writes[-1],
            (
                "/workspace/.verix-generated-tests/test_verix_generated.py",
                tests,
                "root",
            ),
        )
        self.assertEqual(
            sandbox.commands.calls[-1]["command"],
            "chmod -R a-w /workspace/.verix-generated-tests",
        )

    def test_rejects_commands_without_an_active_workspace(self) -> None:
        runner = E2BTestRunner(sandbox_factory=lambda *args, **kwargs: FakeSandbox())
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "active workspace"):
                runner.run_repository_command(
                    Path(directory),
                    ["python", "-m", "pytest"],
                )
