#!/usr/bin/env python3
"""Fail-closed checks for the v3 company ResearchOutput contract.

This validator checks structure and a small set of semantic safety invariants.
It does not verify that a source is true; source entailment remains an
evidence-review task.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FORBIDDEN_TOP_LEVEL_KEYS = {
    "final_score",
    "overall_score",
    "conviction_score",
    "buy_score",
    "expected_return",
    "win_probability",
    "price_target",
}

BOTTLENECK_DIMENSIONS = {
    "supplier_concentration",
    "substitutability",
    "qualification_burden",
    "expansion_lead_time",
    "customer_urgency",
    "capacity_visibility",
    "pricing_power",
    "economic_value_capture",
}


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


def validate_schema_document(value: Any, schema_path: Path) -> list[str]:
    if not schema_path.is_file():
        return [f"missing schema: {schema_path}"]
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid schema: {exc}"]
    return _schema_errors(value, schema, "document")


def validate_component(value: Any, schema_path: Path) -> list[str]:
    """Validate a v3 component and its cross-field safety invariants."""
    errors = validate_schema_document(value, schema_path)
    if not isinstance(value, dict):
        return errors
    name = schema_path.name
    if name == "bottleneck-assessment.schema.json":
        dimensions = value.get("dimensions")
        seen = [item.get("dimension") for item in dimensions if isinstance(item, dict)] if isinstance(dimensions, list) else []
        missing = sorted(BOTTLENECK_DIMENSIONS - set(seen))
        duplicates = sorted({item for item in seen if seen.count(item) > 1})
        errors.extend(f"bottleneck:missing_dimension:{item}" for item in missing)
        errors.extend(f"bottleneck:duplicate_dimension:{item}" for item in duplicates)
        cutoff = parse_iso(value.get("research_cutoff"))
        assessed = parse_iso(value.get("assessment_as_of"))
        if cutoff is not None and assessed is not None and assessed > cutoff:
            errors.append("bottleneck:assessment_after_cutoff")
    elif name == "company-profile.schema.json":
        if value.get("identity_status") == "resolved":
            for field in ("ticker", "exchange", "market", "quote_currency"):
                if not value.get(field):
                    errors.append(f"company:resolved_identity_missing:{field}")
        cutoff = parse_iso(value.get("research_cutoff"))
        as_of = parse_iso(value.get("as_of"))
        if cutoff is not None and as_of is not None and as_of > cutoff:
            errors.append("company:as_of_after_cutoff")
    elif name == "market-snapshot.schema.json":
        status = value.get("data_status")
        if status in {"current", "delayed"} and (
            value.get("price") is None or value.get("price_as_of") is None
        ):
            errors.append("market:current_or_delayed_price_requires_value_and_as_of")
        if value.get("price") is not None and value.get("price_as_of") is None:
            errors.append("market:price_requires_as_of")
        if value.get("market_cap") is not None and value.get("market_cap_as_of") is None:
            errors.append("market:market_cap_requires_as_of")
        if value.get("market_cap_basis") in {"price_times_basic_shares", "price_times_diluted_shares"}:
            if value.get("price") is None or value.get("shares_outstanding") is None:
                errors.append("market:calculated_market_cap_requires_price_and_shares")
        cutoff = parse_iso(value.get("research_cutoff"))
        for field in ("price_as_of", "market_cap_as_of", "shares_as_of"):
            timestamp = parse_iso(value.get(field))
            if cutoff is not None and timestamp is not None and timestamp > cutoff:
                errors.append(f"market:{field}_after_cutoff")
    return errors


def validate_output(value: dict[str, Any], schema_root: Path) -> list[str]:
    schema_path = schema_root / "research-output.schema.json"
    errors: list[str] = []
    errors.extend(
        f"research_output:{error}"
        for error in validate_schema_document(value, schema_path)
    )

    forbidden = sorted(FORBIDDEN_TOP_LEVEL_KEYS.intersection(value))
    errors.extend(f"research_output:forbidden additive scoring/forecast key:{key}" for key in forbidden)

    cutoff = parse_iso(value.get("research_cutoff"))
    as_of = parse_iso(value.get("as_of"))
    if cutoff is not None and as_of is not None and as_of > cutoff:
        errors.append("research_output:as_of_after_research_cutoff")

    access = value.get("access_level")
    partition = value.get("source_partition")
    if access and partition and access != partition:
        errors.append("research_output:access_partition_mismatch")
    lineage = value.get("source_lineage")
    if isinstance(lineage, list) and partition:
        for index, item in enumerate(lineage):
            if isinstance(item, dict) and item.get("source_partition") != partition:
                errors.append(f"research_output:lineage_partition_mismatch:{index}")

    if value.get("research_language") not in {
        "research_priority_only",
        "conditional_interest",
        "insufficient_evidence",
        None,
    }:
        errors.append("research_output:invalid_research_language")
    return errors


def validate_file(path: Path, schema_root: Path) -> list[str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: invalid JSON ({exc})"]
    if not isinstance(value, dict):
        return [f"{path}: top-level object required"]
    return [f"{path}: {error}" for error in validate_output(value, schema_root)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="ResearchOutput JSON file")
    parser.add_argument("--schema-root", type=Path, default=Path(__file__).parents[1] / "schemas")
    args = parser.parse_args()
    errors = validate_file(args.path.resolve(), args.schema_root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: ResearchOutput v3 {args.path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
