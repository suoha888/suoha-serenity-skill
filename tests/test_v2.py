import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "scripts"))

from build_local_index import (
    build_index,
    holdout_ids_for_partition as index_holdout_ids_for_partition,
    safe_fts_query,
    search_index,
)
from build_runtime import build_runtime
from distill_archive import (
    distill,
    holdout_ids_for_partition,
    parse_timestamp,
    run as run_distillation,
)
from verify_runtime import verify_runtime


SOURCE_HASH = "a" * 64


def normalized_record(
    record_id: str,
    partition: str,
    created_at: str,
    text: str,
) -> dict:
    return {
        "id": record_id,
        "text": text,
        "created_at": created_at,
        "captured_at": "2026-08-29T00:00:00Z",
        "record_hash": SOURCE_HASH,
        "access_level": partition,
        "source_partition": partition,
        "conversation_id": record_id,
        "parent_id": None,
        "is_reply": False,
        "is_quote": False,
        "media": [],
        "provenance": {
            "source_partition": partition,
            "source_file": f"{partition}.json",
            "source_record_id": record_id,
            "source_sha256": SOURCE_HASH,
        },
    }


class SurohaSerenityV2Tests(unittest.TestCase):
    def test_distillation_is_partitioned_and_respects_as_of_cutoff(self):
        records = [
            normalized_record(
                "p-keep",
                "public",
                "2025-06-01T00:00:00Z",
                "AI supply chain bottleneck capacity may constrain deployment.",
            ),
            normalized_record(
                "p-future",
                "public",
                "2026-06-01T00:00:00Z",
                "Future evidence should not enter an as-of replay.",
            ),
        ]
        cutoff = parse_timestamp("2025-12-31T23:59:59Z")
        layers = distill(records, "public", cutoff, min_support=1)

        self.assertEqual(
            {row["root_post_id"] for row in layers["context-packs.jsonl"]},
            {"p-keep"},
        )
        self.assertTrue(layers["claims.jsonl"])
        self.assertTrue(
            all(
                row["source_record_ids"] == ["p-keep"]
                for row in layers["claims.jsonl"]
            )
        )
        for filename, rows in layers.items():
            for row in rows:
                if "access_level" in row:
                    self.assertEqual(row["access_level"], "public", filename)
                if "source_partition" in row:
                    self.assertEqual(row["source_partition"], "public", filename)

    def test_distillation_rejects_mixed_access_records(self):
        records = [normalized_record("sub-1", "subscription", "2025-06-01T00:00:00Z", "private note")]
        with self.assertRaises(ValueError):
            distill(records, "public", None, min_support=1)

    def test_local_index_keeps_same_record_id_separate_by_partition(self):
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory) / "data"
            for partition in ("public", "subscription"):
                posts_path = data_root / "normalized" / partition / "posts.jsonl"
                posts_path.parent.mkdir(parents=True, exist_ok=True)
                posts_path.write_text(
                    json.dumps(
                        normalized_record(
                            "same-id",
                            partition,
                            "2025-06-01T00:00:00Z",
                            f"{partition} bottleneck note",
                        ),
                        ensure_ascii=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            database = data_root / "indexes" / "serenity.sqlite3"
            counts = build_index(data_root, database, {"public", "subscription"})

            self.assertEqual(counts["records"], 2)
            self.assertEqual(
                search_index(database, "bottleneck", "public", 20)[0]["partition"],
                "public",
            )
            connection = sqlite3.connect(database)
            try:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM records").fetchone()[0], 2)
            finally:
                connection.close()

    def test_local_index_excludes_holdout_by_default_and_guards_search(self):
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory) / "data"
            posts_path = data_root / "normalized" / "public" / "posts.jsonl"
            posts_path.parent.mkdir(parents=True, exist_ok=True)
            rows = [
                normalized_record("p-keep", "public", "2025-06-01T00:00:00Z", "keep bottleneck"),
                normalized_record("p-holdout", "public", "2026-01-01T00:00:00Z", "holdout bottleneck"),
            ]
            posts_path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            holdout_root = data_root / "holdout"
            holdout_root.mkdir(parents=True)
            (holdout_root / "temporal-holdout.jsonl").write_text(
                json.dumps(rows[1]) + "\n",
                encoding="utf-8",
            )
            (holdout_root / "temporal-holdout-manifest.json").write_text(
                json.dumps({"record_ids": ["p-holdout"]}),
                encoding="utf-8",
            )
            self.assertEqual(index_holdout_ids_for_partition(data_root, "public"), {"p-holdout"})

            database = data_root / "indexes" / "serenity.sqlite3"
            sealed_counts = build_index(data_root, database, {"public"})
            self.assertEqual(sealed_counts["records"], 1)
            self.assertEqual(search_index(database, "bottleneck", "public", 20)[0]["record_id"], "p-keep")

            open_counts = build_index(data_root, database, {"public"}, include_holdout=True)
            self.assertEqual(open_counts["records"], 2)
            with self.assertRaises(ValueError):
                search_index(database, "bottleneck", "public", 20)
            self.assertEqual(
                len(search_index(database, "bottleneck", "public", 20, include_holdout=True)),
                2,
            )
            self.assertEqual(
                len(
                    search_index(
                        database,
                        "bottleneck",
                        "public",
                        20,
                        include_holdout=True,
                        as_of="2025-12-31T23:59:59Z",
                    )
                ),
                1,
            )
            with self.assertRaises(ValueError):
                search_index(
                    database,
                    "bottleneck",
                    "public",
                    20,
                    include_holdout=True,
                    as_of="2025-12-31T23:59:59",
                )

    def test_fts_query_is_quoted_and_empty_query_fails_closed(self):
        self.assertEqual(safe_fts_query("bottleneck OR"), '"bottleneck" AND "OR"')
        with self.assertRaises(ValueError):
            safe_fts_query("!!!")

    def test_runtime_build_and_verification_are_hash_consistent(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "suoha-serenity-skill"
            manifest = build_runtime(SOURCE_ROOT, runtime_root)
            report = verify_runtime(SOURCE_ROOT, runtime_root)

            self.assertEqual(manifest["skill_name"], "suoha-serenity-skill")
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["expected_file_count"], report["actual_file_count"])

    def test_distillation_output_must_be_partition_named(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "posts.jsonl"
            input_path.write_text(
                json.dumps(
                    normalized_record(
                        "p-1",
                        "public",
                        "2025-06-01T00:00:00Z",
                        "A public bottleneck note",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                run_distillation(
                    input_path,
                    Path(directory) / "derived",
                    "public",
                    None,
                    1,
                    replace=True,
                )

    def test_runtime_output_must_use_the_skill_name(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                build_runtime(SOURCE_ROOT, Path(directory) / "wrong-name")

    def test_holdout_ids_are_filtered_by_access_partition(self):
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory) / "data"
            holdout_root = data_root / "holdout"
            holdout_root.mkdir(parents=True)
            rows = [
                normalized_record("p-1", "public", "2026-01-01T00:00:00Z", "public"),
                normalized_record("s-1", "subscription", "2026-01-01T00:00:00Z", "subscription"),
            ]
            (holdout_root / "temporal-holdout.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            (holdout_root / "temporal-holdout-manifest.json").write_text(
                json.dumps({"record_ids": ["p-1", "s-1"]}),
                encoding="utf-8",
            )

            self.assertEqual(holdout_ids_for_partition(data_root, "public"), {"p-1"})
            self.assertEqual(holdout_ids_for_partition(data_root, "subscription"), {"s-1"})


if __name__ == "__main__":
    unittest.main()
