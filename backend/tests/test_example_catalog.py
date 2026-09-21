"""Validate the deterministic deterministic examples without executing their code."""

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPOSITORY_ROOT / "examples" / "python" / "catalog.json"
COMMIT_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
EXPECTED_CATEGORIES = {
    "normal",
    "boundary",
    "invalid_input",
    "error_handling",
}
ALLOWED_STRATEGIES = {"black_box", "gray_box"}
ALLOWED_EXISTING_OUTCOMES = {"passed", "failed", "no_tests"}


class ExampleCatalogTests(unittest.TestCase):
    """Keep example contracts pinned, complete, and reproducible as data."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    def test_catalog_pins_one_public_repository_revision(self) -> None:
        self.assertEqual(self.catalog["schema_version"], 1)
        self.assertEqual(
            self.catalog["repository_url"],
            "https://github.com/sehtaj/Verix",
        )
        self.assertIsNotNone(
            COMMIT_SHA_PATTERN.fullmatch(self.catalog["revision"])
        )
        self.assertEqual(
            self.catalog["publication_status"],
            "pending_approved_push",
        )

    def test_examples_have_unique_safe_targets_and_explicit_contracts(self) -> None:
        examples = self.catalog["examples"]
        self.assertGreaterEqual(len(examples), 3)
        self.assertEqual(len({example["id"] for example in examples}), len(examples))

        for example in examples:
            with self.subTest(example=example["id"]):
                subdirectory = self._safe_path(example["subdirectory"])
                target_path = self._safe_path(example["target_path"])
                behavior_path = self._safe_path(example["behavior_source"]["path"])
                self.assertTrue(target_path.is_relative_to(subdirectory))
                self.assertTrue(behavior_path.is_relative_to(subdirectory))
                self.assertEqual(
                    example["behavior_source"]["kind"],
                    "explicit_specification",
                )
                self.assertTrue(example["known_bug"].strip())
                self.assertIn(
                    example["expected_existing_outcome"],
                    ALLOWED_EXISTING_OUTCOMES,
                )
                self.assertEqual(example["expected_exposing_outcome"], "failed")
                self.assertIsInstance(example["assumptions"], list)
                self.assertTrue(example["untested"])

    def test_each_example_requires_all_test_categories_and_safe_strategies(self) -> None:
        for example in self.catalog["examples"]:
            with self.subTest(example=example["id"]):
                cases = example["required_test_cases"]
                self.assertEqual(
                    {case["category"] for case in cases},
                    EXPECTED_CATEGORIES,
                )
                self.assertTrue(
                    all(case["strategy"] in ALLOWED_STRATEGIES for case in cases)
                )
                self.assertTrue(all(case["behavior"].strip() for case in cases))
                self.assertIn("black_box", {case["strategy"] for case in cases})
                self.assertIn("gray_box", {case["strategy"] for case in cases})

    def test_declared_example_files_match_the_pinned_content_hashes(self) -> None:
        for example in self.catalog["examples"]:
            project_directory = REPOSITORY_ROOT.joinpath(
                *PurePosixPath(example["subdirectory"]).parts
            )
            declared_files = example["files"]
            actual_files = {
                path.relative_to(project_directory).as_posix()
                for path in project_directory.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            }
            with self.subTest(example=example["id"]):
                self.assertEqual(set(declared_files), actual_files)
                for relative_path, expected_hash in declared_files.items():
                    content = (project_directory / relative_path).read_bytes()
                    self.assertEqual(sha256(content).hexdigest(), expected_hash)

    @staticmethod
    def _safe_path(value: str) -> PurePosixPath:
        path = PurePosixPath(value)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise AssertionError(f"Unsafe catalog path: {value}")
        return path


if __name__ == "__main__":
    unittest.main()
