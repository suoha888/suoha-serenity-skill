import json
import sys
import tempfile
import unittest
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "scripts"))

from distill_archive import DISTILLED_LAYER_FILES, run


class DistillationPathSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data_root = Path(self.temp.name) / "data"
        self.normalized = self.data_root / "normalized" / "public"
        self.normalized.mkdir(parents=True)
        self.input_path = self.normalized / "posts.jsonl"
        self.input_path.write_text("", encoding="utf-8")
        self.output_root = self.data_root / "derived" / "public"

    def tearDown(self):
        self.temp.cleanup()

    def distill(self, *, input_path=None, output_root=None, replace=True):
        return run(
            input_path or self.input_path,
            output_root or self.output_root,
            "public",
            None,
            1,
            replace,
            data_root=self.data_root,
        )

    def test_arbitrary_directory_named_public_is_never_a_replace_target(self):
        outside = Path(self.temp.name) / "important" / "public"
        outside.mkdir(parents=True)
        sentinel = outside / "keep.txt"
        sentinel.write_text("user data", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "exactly the selected derived partition"):
            self.distill(output_root=outside)

        self.assertEqual(sentinel.read_text(encoding="utf-8"), "user data")

    def test_input_must_be_inside_the_selected_normalized_partition(self):
        raw_input = self.data_root / "raw" / "posts.jsonl"
        raw_input.parent.mkdir(parents=True)
        raw_input.write_text("", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "inside the normalized public partition"):
            self.distill(input_path=raw_input)

        self.assertFalse(self.output_root.exists())

    def test_unmanaged_existing_output_is_preserved(self):
        self.output_root.mkdir(parents=True)
        sentinel = self.output_root / "keep.txt"
        sentinel.write_text("user data", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "unmanaged directory"):
            self.distill(replace=True)

        self.assertEqual(sentinel.read_text(encoding="utf-8"), "user data")

    def test_replacement_keeps_the_previous_generated_output_recoverable(self):
        self.distill(replace=False)
        old_manifest = (self.output_root / "distillation-manifest.json").read_text(
            encoding="utf-8"
        )
        old_files = set(DISTILLED_LAYER_FILES) | {"distillation-manifest.json"}
        self.assertEqual(
            {path.name for path in self.output_root.iterdir() if path.is_file()},
            old_files,
        )

        new_manifest = self.distill(replace=True)
        backup_path = Path(new_manifest["replacement_backup"])

        self.assertTrue(backup_path.is_dir())
        self.assertEqual(
            (backup_path / "distillation-manifest.json").read_text(encoding="utf-8"),
            old_manifest,
        )
        self.assertEqual(
            json.loads((self.output_root / "distillation-manifest.json").read_text(encoding="utf-8"))[
                "replacement_backup"
            ],
            backup_path.as_posix(),
        )


if __name__ == "__main__":
    unittest.main()
