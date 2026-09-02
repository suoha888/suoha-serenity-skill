#!/usr/bin/env python3
"""Build and query a local SQLite + FTS5 index for normalized records.

JSONL remains canonical.  The index is a disposable local acceleration layer,
never a source of truth and never part of the generated public runtime.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PARTITIONS = {"public", "subscription"}
TOKEN_RE = re.compile(r"[A-Za-z0-9_.$@-]+|[\u4e00-\u9fff]")


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected an object")
            yield value


def holdout_ids_for_partition(data_root: Path, partition: str) -> set[str]:
    manifest_path = data_root / "holdout" / "temporal-holdout-manifest.json"
    if not manifest_path.is_file():
        return set()
    holdout_path = data_root / "holdout" / "temporal-holdout.jsonl"
    if not holdout_path.is_file():
        raise ValueError("temporal holdout manifest exists but holdout JSONL is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_ids = manifest.get("record_ids", [])
    if not isinstance(raw_ids, list) or len(raw_ids) != len({str(value) for value in raw_ids}):
        raise ValueError("temporal holdout manifest record_ids must be a unique list")
    manifest_ids = {str(value) for value in raw_ids}
    rows = list(read_jsonl(holdout_path))
    row_ids = {str(row.get("id")) for row in rows}
    if row_ids != manifest_ids or len(rows) != len(row_ids):
        raise ValueError("temporal holdout JSONL does not match its manifest")
    selected: set[str] = set()
    for row in rows:
        row_partition = str(row.get("access_level") or "")
        if row_partition not in PARTITIONS:
            raise ValueError("temporal holdout contains an invalid access level")
        if row_partition == partition:
            selected.add(str(row.get("id")))
    return selected


def safe_fts_query(query: str) -> str:
    tokens = TOKEN_RE.findall(query or "")
    if not tokens:
        raise ValueError("search query has no searchable tokens")
    # Each token is quoted so user text cannot add FTS operators or SQL syntax.
    return " AND ".join('"' + token.replace('"', '""') + '"' for token in tokens)


def normalize_as_of(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("as_of must be a timezone-aware ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("as_of must be a timezone-aware ISO timestamp")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS records (
            record_id TEXT NOT NULL,
            partition TEXT NOT NULL CHECK (partition IN ('public','subscription')),
            access_level TEXT NOT NULL,
            created_at TEXT,
            captured_at TEXT,
            conversation_id TEXT,
            parent_id TEXT,
            text TEXT NOT NULL,
            record_hash TEXT NOT NULL,
            source_file TEXT NOT NULL,
            PRIMARY KEY (partition, record_id)
        );
        CREATE INDEX IF NOT EXISTS records_partition_time
            ON records (partition, created_at, record_id);
        CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(
            record_id UNINDEXED,
            partition UNINDEXED,
            text,
            tokenize = 'unicode61'
        );
        CREATE TABLE IF NOT EXISTS entities (
            entity_id TEXT NOT NULL,
            label TEXT NOT NULL,
            partition TEXT NOT NULL,
            source_record_ids TEXT NOT NULL,
            PRIMARY KEY (entity_id, partition)
        );
        CREATE TABLE IF NOT EXISTS claims (
            claim_id TEXT PRIMARY KEY,
            partition TEXT NOT NULL,
            access_level TEXT NOT NULL,
            as_of TEXT,
            evidence_state TEXT NOT NULL,
            text TEXT NOT NULL,
            source_record_ids TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS evidence (
            evidence_id TEXT PRIMARY KEY,
            partition TEXT NOT NULL,
            access_level TEXT NOT NULL,
            published_at TEXT,
            known_at TEXT,
            independence_group TEXT NOT NULL,
            source TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS theses (
            thesis_id TEXT PRIMARY KEY,
            partition TEXT NOT NULL,
            access_level TEXT NOT NULL,
            state TEXT NOT NULL,
            statement TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS thesis_events (
            event_id TEXT PRIMARY KEY,
            thesis_id TEXT NOT NULL,
            partition TEXT NOT NULL,
            access_level TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_at TEXT
        );
        CREATE TABLE IF NOT EXISTS methods (
            method_id TEXT PRIMARY KEY,
            partition TEXT NOT NULL,
            access_level TEXT NOT NULL,
            review_status TEXT NOT NULL,
            name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS relations (
            relation_id TEXT PRIMARY KEY,
            partition TEXT NOT NULL,
            access_level TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL
        );
        """
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_index(
    data_root: Path,
    database: Path,
    partitions: set[str],
    *,
    include_holdout: bool = False,
) -> dict[str, int]:
    if not partitions or not partitions <= PARTITIONS:
        raise ValueError(f"partitions must be a non-empty subset of {sorted(PARTITIONS)}")
    database = database.resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    counts = {"records": 0, "claims": 0, "evidence": 0, "theses": 0, "thesis_events": 0, "methods": 0, "relations": 0}
    excluded_holdout_count = 0
    try:
        connection.executescript(
            """
            DROP TABLE IF EXISTS records_fts;
            DROP TABLE IF EXISTS records;
            DROP TABLE IF EXISTS entities;
            DROP TABLE IF EXISTS claims;
            DROP TABLE IF EXISTS evidence;
            DROP TABLE IF EXISTS theses;
            DROP TABLE IF EXISTS thesis_events;
            DROP TABLE IF EXISTS methods;
            DROP TABLE IF EXISTS relations;
            DROP TABLE IF EXISTS metadata;
            """
        )
        create_schema(connection)
        for partition in sorted(partitions):
            posts_path = data_root / "normalized" / partition / "posts.jsonl"
            if not posts_path.is_file():
                raise FileNotFoundError(posts_path)
            excluded_ids = set() if include_holdout else holdout_ids_for_partition(data_root, partition)
            excluded_holdout_count += len(excluded_ids)
            for record in read_jsonl(posts_path):
                if record.get("access_level") != partition or record.get("source_partition") != partition:
                    raise ValueError(f"access partition mismatch for record {record.get('id')}")
                if str(record.get("id")) in excluded_ids:
                    continue
                provenance = record.get("provenance") or {}
                connection.execute(
                    """
                    INSERT INTO records
                    (record_id, partition, access_level, created_at, captured_at,
                     conversation_id, parent_id, text, record_hash, source_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(record.get("id")),
                        partition,
                        str(record.get("access_level")),
                        record.get("created_at"),
                        record.get("captured_at"),
                        record.get("conversation_id"),
                        record.get("parent_id"),
                        str(record.get("text") or ""),
                        str(record.get("record_hash") or ""),
                        str(provenance.get("source_file") or ""),
                    ),
                )
                connection.execute(
                    "INSERT INTO records_fts (record_id, partition, text) VALUES (?, ?, ?)",
                    (str(record.get("id")), partition, str(record.get("text") or "")),
                )
                counts["records"] += 1

            derived_root = data_root / "derived" / partition
            for row in read_jsonl(derived_root / "entities.jsonl") if (derived_root / "entities.jsonl").is_file() else []:
                connection.execute(
                    "INSERT INTO entities VALUES (?, ?, ?, ?)",
                    (row["entity_id"], row["label"], partition, _json(row.get("source_record_ids", []))),
                )
            for row in read_jsonl(derived_root / "claims.jsonl") if (derived_root / "claims.jsonl").is_file() else []:
                connection.execute(
                    "INSERT INTO claims VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (row["claim_id"], partition, row["access_level"], row.get("as_of"), row["evidence_state"], row["text"], _json(row.get("source_record_ids", []))),
                )
                counts["claims"] += 1
            for row in read_jsonl(derived_root / "evidence.jsonl") if (derived_root / "evidence.jsonl").is_file() else []:
                connection.execute(
                    "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (row["evidence_id"], partition, row["access_level"], row.get("published_at"), row.get("known_at"), row["independence_group"], row["source"]),
                )
                counts["evidence"] += 1
            for row in read_jsonl(derived_root / "theses.jsonl") if (derived_root / "theses.jsonl").is_file() else []:
                connection.execute(
                    "INSERT INTO theses VALUES (?, ?, ?, ?, ?)",
                    (row["thesis_id"], partition, row["access_level"], row["state"], row["statement"]),
                )
                counts["theses"] += 1
            for row in read_jsonl(derived_root / "thesis-events.jsonl") if (derived_root / "thesis-events.jsonl").is_file() else []:
                connection.execute(
                    "INSERT INTO thesis_events VALUES (?, ?, ?, ?, ?, ?)",
                    (row["event_id"], row["thesis_id"], partition, row["access_level"], row["event_type"], row.get("event_at")),
                )
                counts["thesis_events"] += 1
            for row in read_jsonl(derived_root / "method-cards.jsonl") if (derived_root / "method-cards.jsonl").is_file() else []:
                connection.execute(
                    "INSERT INTO methods VALUES (?, ?, ?, ?, ?)",
                    (row["method_id"], partition, row["access_level"], row["review_status"], row["name"]),
                )
                counts["methods"] += 1
            for row in read_jsonl(derived_root / "relations.jsonl") if (derived_root / "relations.jsonl").is_file() else []:
                connection.execute(
                    "INSERT INTO relations VALUES (?, ?, ?, ?, ?, ?)",
                    (row["relation_id"], partition, row["access_level"], row["relation_type"], row["source_id"], row["target_id"]),
                )
                counts["relations"] += 1
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES ('partitions', ?)",
            (_json(sorted(partitions)),),
        )
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES ('canonical_format', 'jsonl')"
        )
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES ('holdout_excluded', ?)",
            ("false" if include_holdout else "true",),
        )
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES ('excluded_holdout_count', ?)",
            (str(excluded_holdout_count),),
        )
        connection.commit()
    finally:
        connection.close()
    return counts


def search_index(
    database: Path,
    query: str,
    access_level: str,
    limit: int,
    *,
    include_holdout: bool = False,
    as_of: str | None = None,
) -> list[dict[str, Any]]:
    if access_level not in PARTITIONS:
        raise ValueError("access_level must be public or subscription")
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    fts_query = safe_fts_query(query)
    normalized_as_of = normalize_as_of(as_of)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
        if not include_holdout and metadata.get("holdout_excluded") != "true":
            raise ValueError("index holdout status is not sealed; use --include-holdout only for evaluator queries")
        sql = """
            SELECT r.record_id, r.partition, r.created_at, r.conversation_id,
                   r.parent_id, r.text, r.source_file
            FROM records_fts f
            JOIN records r ON r.record_id = f.record_id AND r.partition = f.partition
            WHERE f.partition = ? AND r.access_level = ? AND f.text MATCH ?
        """
        parameters: list[Any] = [access_level, access_level, fts_query]
        if normalized_as_of is not None:
            sql += " AND r.created_at IS NOT NULL AND r.created_at <= ?"
            parameters.append(normalized_as_of)
        sql += " ORDER BY r.created_at DESC, r.record_id LIMIT ?"
        parameters.append(limit)
        rows = connection.execute(sql, parameters).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/serenity"))
    parser.add_argument("--database", type=Path)
    parser.add_argument("--partition", choices=["public", "subscription", "all"], default="public")
    parser.add_argument("--query")
    parser.add_argument("--access-level", choices=sorted(PARTITIONS), default="public")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--as-of",
        help="timezone-aware ISO cutoff; only records known by this time are returned",
    )
    parser.add_argument(
        "--include-holdout",
        action="store_true",
        help="explicit evaluator-only override for building or querying an index with the frozen holdout",
    )
    args = parser.parse_args()
    database = args.database or args.data_root / "indexes" / "serenity.sqlite3"
    try:
        if args.query:
            rows = search_index(
                database,
                args.query,
                args.access_level,
                args.limit,
                include_holdout=args.include_holdout,
                as_of=args.as_of,
            )
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            partitions = PARTITIONS if args.partition == "all" else {args.partition}
            counts = build_index(
                args.data_root,
                database,
                partitions,
                include_holdout=args.include_holdout,
            )
            print(f"OK: built local index -> {database.resolve()}")
            print(json.dumps(counts, ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
