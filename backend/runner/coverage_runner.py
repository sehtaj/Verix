"""Trusted container entrypoint for pytest plus selected-file branch evidence."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


COVERAGE_SENTINEL = "VERIX_BRANCH_COVERAGE="
WORKSPACE = Path("/workspace")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("pytest_arguments", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()

    target = Path(arguments.target)
    try:
        relative_target = target.relative_to(WORKSPACE)
    except ValueError:
        parser.error("target must be inside /workspace")
    if target.suffix != ".py" or not target.is_file() or target.is_symlink():
        parser.error("target must be an existing regular Python file")

    pytest_arguments = arguments.pytest_arguments
    if pytest_arguments[:1] == ["--"]:
        pytest_arguments = pytest_arguments[1:]

    with tempfile.TemporaryDirectory(prefix="verix-coverage-") as temporary:
        temporary_path = Path(temporary)
        data_file = temporary_path / ".coverage"
        report_file = temporary_path / "coverage.json"
        execution = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "run",
                "--rcfile=/dev/null",
                "--branch",
                f"--source={target.parent}",
                "--omit=/workspace/.verix-venv/*,/workspace/.verix-generated-tests/*",
                f"--data-file={data_file}",
                "-m",
                "pytest",
                *pytest_arguments,
            ],
            cwd=WORKSPACE,
            capture_output=True,
            check=False,
            text=True,
        )
        sys.stdout.write(execution.stdout)
        sys.stdout.write(execution.stderr)

        try:
            report = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "coverage",
                    "json",
                    "--rcfile=/dev/null",
                    f"--data-file={data_file}",
                    f"--include={target}",
                    "-o",
                    str(report_file),
                ],
                cwd=WORKSPACE,
                capture_output=True,
                check=False,
                text=True,
            )
            if report.returncode == 0:
                payload = _coverage_payload(report_file, relative_target.as_posix())
                sys.stdout.write(
                    f"{COVERAGE_SENTINEL}{json.dumps(payload, separators=(',', ':'))}\n"
                )
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    return execution.returncode


def _coverage_payload(report_file: Path, target_path: str) -> dict[str, object]:
    report = json.loads(report_file.read_text(encoding="utf-8"))
    files = report.get("files", {})
    target_report = next(
        (
            value
            for path, value in files.items()
            if Path(path).resolve() == (WORKSPACE / target_path).resolve()
        ),
        None,
    )
    if not isinstance(target_report, dict):
        raise ValueError("Coverage report omitted the selected target.")
    summary = target_report.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("Coverage report omitted the selected target summary.")
    return {
        "target_path": target_path,
        "total_branches": summary.get("num_branches"),
        "executed_branches": target_report.get("executed_branches", []),
    }


if __name__ == "__main__":
    raise SystemExit(main())
