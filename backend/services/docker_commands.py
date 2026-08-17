"""Build hardened Docker commands without launching containers."""

import os
from pathlib import Path


class DockerCommandBuilder:
    """Construct deterministic commands for Verix's trusted runner image."""

    @staticmethod
    def build_pasted_code_command(
        workspace_path: Path,
        container_name: str,
        *,
        runner_image: str,
    ) -> list[str]:
        """Build the isolated pytest command used for pasted Python code."""
        return [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--pids-limit",
            "64",
            "--memory",
            "256m",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--mount",
            f"type=bind,source={workspace_path},target=/workspace,readonly",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            runner_image,
            "-p",
            "no:cacheprovider",
        ]

    @staticmethod
    def build_repository_command(
        workspace_path: Path,
        container_name: str,
        command: list[str],
        *,
        allow_network: bool,
        environment: dict[str, str] | None,
        workspace_read_only: bool,
        runner_image: str,
        tox_directory: str,
    ) -> list[str]:
        """Build a resource-bounded command for a repository workspace."""
        environment_options = [
            option
            for name, value in sorted((environment or {}).items())
            for option in ("--env", f"{name}={value}")
        ]
        workspace_mount = (
            f"type=bind,source={workspace_path.resolve()},target=/workspace"
            + (",readonly" if workspace_read_only else "")
        )
        tox_work_path = workspace_path / tox_directory
        if tox_work_path.is_symlink() or (
            tox_work_path.exists() and not tox_work_path.is_dir()
        ):
            raise ValueError(
                f"Repository contains an invalid {tox_directory} path."
            )
        tox_work_path.mkdir(exist_ok=True)
        os.chmod(tox_work_path, 0o777)

        return [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "bridge" if allow_network else "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--pids-limit",
            "128",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=128m",
            "--tmpfs",
            "/home/runner:rw,nosuid,size=64m,uid=1000,gid=1000,mode=700",
            "--mount",
            workspace_mount,
            "--mount",
            f"type=bind,source={tox_work_path.resolve()},target=/tox-work",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            *environment_options,
            "--entrypoint",
            command[0],
            runner_image,
            *command[1:],
        ]
