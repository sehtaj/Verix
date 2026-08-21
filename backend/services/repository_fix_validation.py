"""Validate one single-file unified diff without writing repository files."""

import ast
import re

from models.fix_proposal import RepositoryFixProposal


HUNK_HEADER_PATTERN = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$"
)
NO_NEWLINE_MARKER = r"\ No newline at end of file"


def validate_repository_fix_proposal(
    proposal: RepositoryFixProposal,
    source_content: str,
) -> str:
    """Return patched Python text only when one diff applies to the exact source."""
    return apply_repository_fix_patch(
        target_path=proposal.target_path,
        patch=proposal.patch,
        source_content=source_content,
    )


def apply_repository_fix_patch(
    *,
    target_path: str,
    patch: str,
    source_content: str,
) -> str:
    """Apply one exact source-only diff in memory without writing any file."""
    patch_lines = patch.splitlines()
    expected_old_header = f"--- a/{target_path}"
    expected_new_header = f"+++ b/{target_path}"
    if len(patch_lines) < 3 or patch_lines[:2] != [
        expected_old_header,
        expected_new_header,
    ]:
        raise ValueError("Repository fix patch must target exactly one selected file.")

    source_lines = source_content.splitlines()
    patched_lines: list[str] = []
    source_position = 0
    patch_position = 2
    change_count = 0
    hunk_count = 0

    while patch_position < len(patch_lines):
        header = HUNK_HEADER_PATTERN.fullmatch(patch_lines[patch_position])
        if header is None:
            raise ValueError("Repository fix patch contains an invalid hunk header.")

        old_start = int(header.group(1))
        old_count = int(header.group(2) or "1")
        new_start = int(header.group(3))
        new_count = int(header.group(4) or "1")
        hunk_source_position = old_start if old_count == 0 else old_start - 1
        if (
            hunk_source_position < source_position
            or hunk_source_position > len(source_lines)
        ):
            raise ValueError("Repository fix patch hunks overlap or exceed the source.")

        patched_lines.extend(source_lines[source_position:hunk_source_position])
        hunk_patched_position = new_start if new_count == 0 else new_start - 1
        if hunk_patched_position != len(patched_lines):
            raise ValueError("Repository fix patch has an invalid new-file position.")
        source_position = hunk_source_position
        patch_position += 1
        hunk_old_count = 0
        hunk_new_count = 0
        hunk_count += 1

        while (
            patch_position < len(patch_lines)
            and HUNK_HEADER_PATTERN.fullmatch(patch_lines[patch_position]) is None
        ):
            patch_line = patch_lines[patch_position]
            patch_position += 1
            if patch_line == NO_NEWLINE_MARKER:
                continue
            if not patch_line or patch_line[0] not in {" ", "+", "-"}:
                raise ValueError("Repository fix patch contains an invalid diff line.")

            prefix = patch_line[0]
            content = patch_line[1:]
            if prefix in {" ", "-"}:
                if (
                    source_position >= len(source_lines)
                    or source_lines[source_position] != content
                ):
                    raise ValueError(
                        "Repository fix patch does not match the selected source."
                    )
                source_position += 1
                hunk_old_count += 1

            if prefix in {" ", "+"}:
                patched_lines.append(content)
                hunk_new_count += 1

            if prefix in {"+", "-"}:
                change_count += 1

        if hunk_old_count != old_count or hunk_new_count != new_count:
            raise ValueError("Repository fix patch hunk line counts are invalid.")

    if hunk_count == 0 or change_count == 0:
        raise ValueError("Repository fix patch must contain a source change.")

    patched_lines.extend(source_lines[source_position:])
    patched_content = "\n".join(patched_lines)
    if source_content.endswith(("\n", "\r")):
        patched_content += "\n"
    if patched_content == source_content:
        raise ValueError("Repository fix patch must change the selected source.")

    try:
        ast.parse(patched_content)
    except (SyntaxError, ValueError):
        raise ValueError(
            "Repository fix patch would produce invalid Python."
        ) from None

    return patched_content
