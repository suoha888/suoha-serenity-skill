#!/usr/bin/env python3
"""Run deterministic safety, schema, provenance, temporal, and drift checks.

This runner does not pretend to measure prose quality.  Human research-quality
and citation-entailment scores must be supplied separately when claiming a
production release.  The automated suite is intentionally fail-closed.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from runtime_common import parse_frontmatter_name
    from verify_runtime import verify_runtime
    from validate_research_output import (
        validate_file as validate_research_output_file,
        validate_component,
    )
except ImportError:
    from scripts.runtime_common import parse_frontmatter_name
    from scripts.verify_runtime import verify_runtime
    from scripts.validate_research_output import (
        validate_file as validate_research_output_file,
        validate_component,
    )


PARTITIONS = {"public", "subscription"}
FIXTURE_GROUPS = {
    "golden": ("golden.jsonl", 20),
    "temporal": ("temporal.jsonl", 20),
    "adversarial": ("adversarial.jsonl", 20),
    "provenance": ("provenance.jsonl", 10),
    "cross_market": ("cross-market.jsonl", 10),
    "conversation": ("conversation.jsonl", 10),
    "company_research": ("company-research.jsonl", 10),
}
RESEARCH_SCHEMA_FILES = (
    "bottleneck-assessment.schema.json",
    "company-profile.schema.json",
    "market-snapshot.schema.json",
    "valuation-snapshot.schema.json",
    "research-output.schema.json",
)
RESEARCH_COMPONENTS = {
    "bottleneck_assessment": "bottleneck-assessment.schema.json",
    "company_profile": "company-profile.schema.json",
    "market_snapshot": "market-snapshot.schema.json",
    "valuation_snapshot": "valuation-snapshot.schema.json",
}
DERIVED_REQUIREMENTS = {
    "context-packs.jsonl": ("context_id", "record_ids", "records", "source_lineage"),
    "entities.jsonl": ("entity_id", "label", "source_record_ids", "source_lineage"),
    "claims.jsonl": ("claim_id", "text", "evidence_ids", "source_record_ids", "source_lineage"),
    "evidence.jsonl": ("evidence_id", "source", "content_hash", "provenance", "source_lineage"),
    "relations.jsonl": ("relation_id", "source_id", "target_id", "source_record_ids", "source_lineage"),
    "theses.jsonl": ("thesis_id", "statement", "source_record_ids", "source_lineage"),
    "thesis-events.jsonl": ("event_id", "thesis_id", "claim_ids", "evidence_ids", "source_record_ids", "source_lineage"),
    "method-cards.jsonl": ("method_id", "name", "reasoning_pattern", "source_claim_ids", "source_record_ids", "source_lineage"),
    "media-triage.jsonl": ("media_id", "post_id", "access_level", "source_record_ids", "source_lineage"),
}
SCHEMA_ENUMS = {
    "access_level": {"public", "subscription", "private", "synthetic"},
    "source_partition": {"public", "subscription", "private", "synthetic"},
    "epistemic_type": {"fact", "inference", "hypothesis", "unknown"},
    "evidence_state": {"supported", "stale", "contradicted", "not_established"},
}
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY-----"),
)
NETWORK_IMPORTS = {
    "requests",
    "httpx",
    "aiohttp",
    "boto3",
    "socket",
    "webbrowser",
    "urllib3",
    "urllib",
    "ftplib",
}

SCHEMA_COLLECTIONS = {
    "normalized": "normalized-post.schema.json",
    "context-packs.jsonl": "context-pack.schema.json",
    "entities.jsonl": "entity.schema.json",
    "claims.jsonl": "claim.schema.json",
    "evidence.jsonl": "evidence.schema.json",
    "relations.jsonl": "relation.schema.json",
    "theses.jsonl": "thesis.schema.json",
    "thesis-events.jsonl": "thesis-event.schema.json",
    "method-cards.jsonl": "method-card.schema.json",
    "media-triage.jsonl": "media-triage.schema.json",
    "manifest": "manifest.schema.json",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: object required")
            result.append(value)
    return result


def parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    raw = str(value)
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _matches_json_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _schema_errors(value: Any, schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type is not None:
        expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_matches_json_type(value, str(item)) for item in expected_types):
            return [f"{path}:type expected {expected_types}, got {type(value).__name__}"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}:const mismatch")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}:enum mismatch")
    if isinstance(value, str):
        if len(value) < int(schema.get("minLength", 0)):
            errors.append(f"{path}:minLength violation")
        pattern = schema.get("pattern")
        if pattern and re.search(str(pattern), value) is None:
            errors.append(f"{path}:pattern violation")
        if schema.get("format") == "date-time" and parse_iso(value) is None:
            errors.append(f"{path}:invalid date-time")
    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)):
            errors.append(f"{path}:minItems violation")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in value]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{path}:uniqueItems violation")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(_schema_errors(item, item_schema, f"{path}[{index}]"))
    if isinstance(value, dict):
        for field in schema.get("required", []):
            if field not in value:
                errors.append(f"{path}:required field missing:{field}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for field, field_schema in properties.items():
                if field in value and isinstance(field_schema, dict):
                    errors.extend(_schema_errors(value[field], field_schema, f"{path}.{field}"))
        if schema.get("additionalProperties") is False and isinstance(properties, dict):
            unknown = sorted(set(value) - set(properties))
            errors.extend(f"{path}:additional property:{field}" for field in unknown)
    return errors


def check_schema_collections(root: Path, data_root: Path, errors: list[str]) -> dict[str, int]:
    schema_root = root / "schemas"
    schemas: dict[str, dict[str, Any]] = {}
    for schema_name in sorted(set(SCHEMA_COLLECTIONS.values())):
        schema_path = schema_root / schema_name
        if not schema_path.is_file():
            errors.append(f"schema_missing:{schema_name}")
            continue
        try:
            schemas[schema_name] = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"schema_invalid:{schema_name}:{exc}")

    checked = {"documents": 0, "rows": 0, "errors": 0}
    targets: list[tuple[str, Path, str, bool]] = []
    for partition in sorted(PARTITIONS):
        targets.append(
            (
                f"normalized:{partition}",
                data_root / "normalized" / partition / "posts.jsonl",
                SCHEMA_COLLECTIONS["normalized"],
                True,
            )
        )
        derived = data_root / "derived" / partition
        for filename in DERIVED_REQUIREMENTS:
            targets.append(
                (
                    f"derived:{partition}/{filename}",
                    derived / filename,
                    SCHEMA_COLLECTIONS[filename],
                    True,
                )
            )
        targets.append(
            (
                f"manifest:{partition}",
                derived / "distillation-manifest.json",
                SCHEMA_COLLECTIONS["manifest"],
                False,
            )
        )

    for label, path, schema_name, is_jsonl in targets:
        schema = schemas.get(schema_name)
        if schema is None or not path.is_file():
            continue
        checked["documents"] += 1
        values: Iterable[Any]
        if is_jsonl:
            values = read_jsonl(path)
        else:
            values = [json.loads(path.read_text(encoding="utf-8"))]
        for index, value in enumerate(values, start=1):
            checked["rows"] += 1
            item_errors = _schema_errors(value, schema, f"{label}:{index}")
            checked["errors"] += len(item_errors)
            if checked["errors"] <= 50:
                errors.extend(f"schema:{item}" for item in item_errors)
    if checked["errors"] > 50:
        errors.append(f"schema:error_report_truncated:{checked['errors']}")
    return checked


def validate_lineage(row: dict[str, Any], partition: str, errors: list[str], label: str) -> None:
    if row.get("access_level") != partition or row.get("source_partition") != partition:
        errors.append(f"{label}: partition/access mismatch")
    lineage = row.get("source_lineage")
    if not isinstance(lineage, list) or not lineage:
        errors.append(f"{label}: source_lineage missing")
        return
    for index, item in enumerate(lineage):
        if not isinstance(item, dict):
            errors.append(f"{label}: lineage {index} is not an object")
            continue
        if item.get("source_partition") != partition:
            errors.append(f"{label}: lineage partition leakage")
        if not item.get("source_file") or not item.get("source_record_id"):
            errors.append(f"{label}: incomplete lineage locator")
        source_hash = str(item.get("source_sha256") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
            errors.append(f"{label}: invalid source hash")


def check_fixtures(root: Path, errors: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for group, (filename, minimum) in FIXTURE_GROUPS.items():
        path = root / "evals" / filename
        if not path.is_file():
            errors.append(f"fixture_missing:{filename}")
            continue
        rows = read_jsonl(path)
        counts[group] = len(rows)
        if len(rows) < minimum:
            errors.append(f"fixture_too_small:{filename}:{len(rows)}<{minimum}")
        seen: set[str] = set()
        for index, row in enumerate(rows, start=1):
            for field in ("case_id", "task", "expected"):
                if field not in row:
                    errors.append(f"fixture_field_missing:{filename}:{index}:{field}")
            case_id = str(row.get("case_id") or "")
            if case_id in seen:
                errors.append(f"fixture_duplicate_id:{filename}:{case_id}")
            seen.add(case_id)
    return counts


def check_research_contract(root: Path, errors: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {"schemas": {}, "fixture": None, "components_fixture": None, "errors": 0}
    for filename in RESEARCH_SCHEMA_FILES:
        path = root / "schemas" / filename
        if not path.is_file():
            errors.append(f"research_schema_missing:{filename}")
            continue
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"research_schema_invalid:{filename}:{exc}")
            continue
        if not isinstance(parsed, dict) or parsed.get("type") != "object":
            errors.append(f"research_schema_not_object:{filename}")
        result["schemas"][filename] = "valid"

    fixture = root / "evals" / "fixtures" / "research-output.synthetic.json"
    if not fixture.is_file():
        errors.append("research_output_fixture_missing")
    else:
        fixture_errors = validate_research_output_file(fixture, root / "schemas")
        result["fixture"] = str(fixture)
        result["errors"] = len(fixture_errors)
        errors.extend(f"research_output:{item}" for item in fixture_errors)

    components_fixture = root / "evals" / "fixtures" / "company-research-components.synthetic.json"
    if not components_fixture.is_file():
        errors.append("research_components_fixture_missing")
    else:
        try:
            components = json.loads(components_fixture.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            components = {}
            errors.append(f"research_components_fixture_invalid:{exc}")
        result["components_fixture"] = str(components_fixture)
        for key, schema_name in RESEARCH_COMPONENTS.items():
            value = components.get(key) if isinstance(components, dict) else None
            schema_errors = (
                [f"missing component:{key}"]
                if value is None
                else validate_component(value, root / "schemas" / schema_name)
            )
            errors.extend(f"research_component:{key}:{item}" for item in schema_errors)
            result["errors"] += len(schema_errors)
    return result


def check_skill_source(root: Path, errors: list[str]) -> dict[str, Any]:
    skill_path = root / "SKILL.md"
    if not skill_path.is_file():
        errors.append("skill_missing")
        return {}
    text = skill_path.read_text(encoding="utf-8")
    name = parse_frontmatter_name(skill_path)
    if name != root.name:
        errors.append(f"skill_name_directory_mismatch:{name!r}!={root.name!r}")
    required_terms = (
        "research_cutoff",
        "UNKNOWN",
        "temporal",
        "provenance",
        "subscription",
        "falsif",
        "untrusted",
        "BottleneckAssessment",
        "CompanyProfile",
        "MarketSnapshot",
        "conditional",
        "single composite",
        "architecture_necessity",
        "validation ladder",
        "reflexivity",
    )
    for term in required_terms:
        if term.lower() not in text.lower():
            errors.append(f"skill_rule_missing:{term}")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            errors.append("secret_pattern_in_skill")
    return {"name": name, "skill_bytes": len(text.encode("utf-8"))}


def check_python_security(root: Path, errors: list[str]) -> dict[str, Any]:
    scanned = 0
    imports: set[str] = set()
    for path in sorted((root / "scripts").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        scanned += 1
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            errors.append(f"python_parse_error:{path.name}:{exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        for pattern in SECRET_PATTERNS:
            if pattern.search(path.read_text(encoding="utf-8")):
                errors.append(f"secret_pattern:{path.name}")
    banned = sorted(imports & NETWORK_IMPORTS)
    if banned:
        errors.append(f"network_imports:{','.join(banned)}")
    return {"python_files": scanned, "network_imports": banned}


def check_normalized(data_root: Path, errors: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for partition in sorted(PARTITIONS):
        path = data_root / "normalized" / partition / "posts.jsonl"
        if not path.is_file():
            errors.append(f"normalized_missing:{partition}")
            continue
        rows = read_jsonl(path)
        counts[partition] = len(rows)
        seen: set[str] = set()
        for index, row in enumerate(rows, start=1):
            label = f"normalized:{partition}:{index}"
            required = ("record_version", "id", "access_level", "source_partition", "captured_at", "provenance", "record_hash")
            for field in required:
                if field not in row:
                    errors.append(f"{label}:missing:{field}")
            if row.get("id") in seen:
                errors.append(f"{label}:duplicate_id")
            seen.add(row.get("id"))
            provenance = row.get("provenance")
            if not isinstance(provenance, dict):
                errors.append(f"{label}: provenance missing")
            else:
                if provenance.get("source_partition") != partition:
                    errors.append(f"{label}: provenance partition mismatch")
                if not provenance.get("source_file") or not provenance.get("source_record_id"):
                    errors.append(f"{label}: provenance locator missing")
                source_hash = str(provenance.get("source_sha256") or "")
                if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
                    errors.append(f"{label}: provenance source hash invalid")
            if row.get("time_status") == "resolved" and row.get("created_at") and parse_iso(row.get("created_at")) is None:
                errors.append(f"{label}:invalid_created_at")
    return counts


def check_derived(data_root: Path, errors: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {"partitions": {}, "objects": 0}
    holdout_ids: dict[str, set[str]] = {partition: set() for partition in PARTITIONS}
    holdout_path = data_root / "holdout" / "temporal-holdout.jsonl"
    if holdout_path.is_file():
        for row in read_jsonl(holdout_path):
            partition = str(row.get("access_level") or "")
            if partition in holdout_ids:
                holdout_ids[partition].add(str(row.get("id")))
    holdout_leakage_reported: set[str] = set()
    for partition in sorted(PARTITIONS):
        directory = data_root / "derived" / partition
        manifest_path = directory / "distillation-manifest.json"
        if not directory.is_dir() or not manifest_path.is_file():
            errors.append(f"derived_missing:{partition}")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("partition") != partition:
            errors.append(f"derived_manifest_partition:{partition}")
        if manifest.get("raw_archive_read") is not False or manifest.get("outcomes_read") is not False:
            errors.append(f"derived_manifest_boundary:{partition}")
        if holdout_path.is_file():
            if manifest.get("holdout_excluded") is not True:
                errors.append(f"derived_manifest_holdout_not_excluded:{partition}")
            if manifest.get("excluded_holdout_count") != len(holdout_ids[partition]):
                errors.append(f"derived_manifest_holdout_count:{partition}")
        partition_counts: dict[str, int] = {}
        for filename, required in DERIVED_REQUIREMENTS.items():
            path = directory / filename
            if not path.is_file():
                errors.append(f"derived_file_missing:{partition}/{filename}")
                continue
            rows = read_jsonl(path)
            partition_counts[filename] = len(rows)
            for index, row in enumerate(rows, start=1):
                label = f"derived:{partition}/{filename}:{index}"
                for field in required:
                    if field not in row:
                        errors.append(f"{label}:missing:{field}")
                if filename != "media-triage.jsonl":
                    validate_lineage(row, partition, errors, label)
                else:
                    validate_lineage(row, partition, errors, label)
                if row.get("known_at") and parse_iso(row.get("known_at")) is None:
                    errors.append(f"{label}:invalid_known_at")
                if row.get("event_at") and parse_iso(row.get("event_at")) is None:
                    errors.append(f"{label}:invalid_event_at")
                row_ids = row.get("source_record_ids")
                if (
                    isinstance(row_ids, list)
                    and holdout_ids[partition].intersection(str(value) for value in row_ids)
                    and partition not in holdout_leakage_reported
                ):
                    errors.append(f"derived_holdout_leakage:{partition}")
                    holdout_leakage_reported.add(partition)
            result["objects"] += len(rows)
        result["partitions"][partition] = partition_counts
    return result


def check_holdout(data_root: Path, errors: list[str]) -> dict[str, Any]:
    holdout_path = data_root / "holdout" / "temporal-holdout.jsonl"
    manifest_path = data_root / "holdout" / "temporal-holdout-manifest.json"
    pilot_path = data_root / "samples" / "pilot-500.jsonl"
    if not holdout_path.is_file() or not manifest_path.is_file():
        errors.append("holdout_missing")
        return {}
    holdout = read_jsonl(holdout_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ids = [str(row.get("id")) for row in holdout]
    if ids != manifest.get("record_ids"):
        errors.append("holdout_manifest_order_mismatch")
    if len(ids) != len(set(ids)):
        errors.append("holdout_duplicate_ids")
    if pilot_path.is_file():
        pilot_ids = {str(row.get("id")) for row in read_jsonl(pilot_path)}
        if pilot_ids.intersection(ids):
            errors.append("holdout_pilot_overlap")
    cutoff = parse_iso(manifest.get("cutoff"))
    if cutoff is None:
        errors.append("holdout_cutoff_invalid")
    else:
        for row in holdout:
            created = parse_iso(row.get("created_at"))
            if created is None or created <= cutoff:
                errors.append(f"holdout_not_after_cutoff:{row.get('id')}")
    return {"records": len(ids), "cutoff": manifest.get("cutoff")}


def check_index(data_root: Path, normalized: dict[str, int], errors: list[str]) -> dict[str, Any]:
    database = data_root / "indexes" / "serenity.sqlite3"
    if not database.is_file():
        errors.append("index_missing")
        return {}
    before = len(errors)
    record_total = 0
    connection = sqlite3.connect(database)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
        if metadata.get("holdout_excluded") != "true":
            errors.append("index_holdout_not_excluded")
        holdout_rows = read_jsonl(data_root / "holdout" / "temporal-holdout.jsonl")
        expected_holdout = len(holdout_rows)
        try:
            indexed_excluded = int(metadata.get("excluded_holdout_count", "-1"))
        except ValueError:
            indexed_excluded = -1
        if indexed_excluded != expected_holdout:
            errors.append("index_holdout_count_mismatch")
        expected_by_partition = {
            partition: normalized.get(partition, 0)
            - sum(row.get("access_level") == partition for row in holdout_rows)
            for partition in PARTITIONS
        }
        actual_by_partition = dict(
            connection.execute(
                "SELECT partition, COUNT(*) FROM records GROUP BY partition"
            ).fetchall()
        )
        record_total = sum(int(value) for value in actual_by_partition.values())
        if actual_by_partition != expected_by_partition:
            errors.append("index_record_count_mismatch")
        holdout_ids = {str(row.get("id")) for row in holdout_rows}
        indexed_ids = {
            str(row[0])
            for row in connection.execute("SELECT record_id FROM records").fetchall()
        }
        if holdout_ids.intersection(indexed_ids):
            errors.append("index_holdout_leakage")
    except (OSError, sqlite3.Error, json.JSONDecodeError) as exc:
        errors.append(f"index_invalid:{exc}")
    finally:
        connection.close()
    return {
        "path": str(database),
        "status": "pass" if len(errors) == before else "fail",
        "records": record_total,
        "errors": len(errors) - before,
    }


def run(root: Path, data_root: Path, runtime_root: Path | None) -> dict[str, Any]:
    errors: list[str] = []
    source = check_skill_source(root, errors)
    security = check_python_security(root, errors)
    fixtures = check_fixtures(root, errors)
    research_contract = check_research_contract(root, errors)
    normalized = check_normalized(data_root, errors)
    derived = check_derived(data_root, errors)
    schema_validation = check_schema_collections(root, data_root, errors)
    holdout = check_holdout(data_root, errors)
    index = check_index(data_root, normalized, errors)
    runtime: dict[str, Any] = {"status": "not_requested"}
    if runtime_root is not None:
        runtime = verify_runtime(root, runtime_root)
        if runtime.get("status") != "pass":
            errors.extend(f"runtime:{item}" for item in runtime.get("errors", []))
    metrics = {
        "schema_validity": 1.0 if schema_validation["errors"] == 0 else 0.0,
        "access_leakage_count": sum(
            1 for error in errors if "leakage" in error or "boundary" in error
        ),
        "temporal_holdout_integrity": 1 if holdout and not any("holdout_" in error for error in errors) else 0,
        "runtime_integrity": 1 if runtime.get("status") in {"pass", "not_requested"} else 0,
        "index_integrity": 1 if index.get("status") == "pass" else 0,
        "research_output_contract": 1 if research_contract["errors"] == 0 else 0,
        "human_quality_status": "not_automated",
        "citation_entailment_status": "requires_human_or_model_evaluator",
    }
    hard_gates = {
        "schema_validity": metrics["schema_validity"] == 1.0,
        "access_leakage": metrics["access_leakage_count"] == 0,
        "temporal_holdout_integrity": metrics["temporal_holdout_integrity"] == 1,
        "runtime_integrity": metrics["runtime_integrity"] == 1,
        "index_integrity": metrics["index_integrity"] == 1,
        "research_output_contract": metrics["research_output_contract"] == 1,
        "fixtures": bool(fixtures) and not any(error.startswith("fixture_") for error in errors),
        "python_security": not security.get("network_imports"),
    }
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "source": source,
        "security": security,
        "fixtures": fixtures,
        "research_contract": research_contract,
        "normalized": normalized,
        "derived": derived,
        "schema_validation": schema_validation,
        "holdout": holdout,
        "index": index,
        "runtime": runtime,
        "metrics": metrics,
        "hard_gates": hard_gates,
        "release_note": "Automated safety gates do not prove investment-research quality or legal clearance.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        report = run(args.root.resolve(), args.data_root.resolve(), args.runtime_root.resolve() if args.runtime_root else None)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{report['status'].upper()}: automated evaluation")
        print(json.dumps(report["hard_gates"], ensure_ascii=False, sort_keys=True))
        for error in report["errors"]:
            print(f"- {error}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
