#!/usr/bin/env python3
"""Fail-closed checks for the v4.2 company ResearchOutput contract.

This validator checks structure and a small set of semantic safety invariants.
It does not verify that a source is true; source entailment remains an
evidence-review task.
"""
from __future__ import annotations

import argparse
import json
import math
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
    "architecture_necessity",
    "yield_manufacturability",
    "merchant_vs_captive_capacity",
    "geographic_regulatory_concentration",
    "capital_intensity",
}

CAPACITY_STATES = {
    "nominal",
    "installed",
    "usable",
    "qualified",
    "merchant",
    "captive",
    "available",
}

VALIDATION_LADDER_STAGES = (
    "architecture_necessity",
    "physical_supply",
    "customer_validation",
    "company_capture",
    "financial_transmission",
    "market_expectations",
)

SUPPORTED_SCHEMA_KEYWORDS = {
    "$id",
    "$schema",
    "additionalProperties",
    "const",
    "description",
    "enum",
    "format",
    "items",
    "maxItems",
    "maximum",
    "minItems",
    "minLength",
    "minimum",
    "pattern",
    "properties",
    "required",
    "title",
    "type",
    "uniqueItems",
}
SUPPORTED_SCHEMA_TYPES = {"array", "boolean", "integer", "null", "number", "object", "string"}


def finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


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
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _schema_definition_errors(schema: Any, path: str) -> list[str]:
    """Reject schema features this dependency-free validator cannot enforce."""
    if not isinstance(schema, dict):
        return [f"{path}:schema must be an object"]
    errors: list[str] = []
    for keyword in sorted(set(schema) - SUPPORTED_SCHEMA_KEYWORDS):
        errors.append(f"{path}:unsupported schema keyword:{keyword}")

    expected_type = schema.get("type")
    if expected_type is not None:
        expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not expected_types or any(
            not isinstance(item, str) or item not in SUPPORTED_SCHEMA_TYPES
            for item in expected_types
        ):
            errors.append(f"{path}:unsupported or invalid schema type")

    required = schema.get("required")
    if required is not None and (
        not isinstance(required, list)
        or any(not isinstance(item, str) for item in required)
    ):
        errors.append(f"{path}:required must be an array of strings")

    properties = schema.get("properties")
    if properties is not None:
        if not isinstance(properties, dict):
            errors.append(f"{path}:properties must be an object")
        else:
            for field, child_schema in properties.items():
                errors.extend(_schema_definition_errors(child_schema, f"{path}.{field}"))

    items = schema.get("items")
    if items is not None:
        errors.extend(_schema_definition_errors(items, f"{path}[]"))

    additional = schema.get("additionalProperties")
    if isinstance(additional, dict):
        errors.extend(_schema_definition_errors(additional, f"{path}.*"))
    elif additional is not None and not isinstance(additional, bool):
        errors.append(f"{path}:additionalProperties must be a boolean or schema")

    for keyword in ("minItems", "maxItems", "minLength"):
        bound = schema.get(keyword)
        if bound is not None and (
            not isinstance(bound, int) or isinstance(bound, bool) or bound < 0
        ):
            errors.append(f"{path}:{keyword} must be a non-negative integer")
    for keyword in ("minimum", "maximum"):
        bound = schema.get(keyword)
        if bound is not None and (
            not isinstance(bound, (int, float)) or isinstance(bound, bool)
        ):
            errors.append(f"{path}:{keyword} must be a number")
    schema_format = schema.get("format")
    if schema_format is not None and schema_format != "date-time":
        errors.append(f"{path}:unsupported schema format:{schema_format}")
    pattern = schema.get("pattern")
    if pattern is not None:
        if not isinstance(pattern, str):
            errors.append(f"{path}:pattern must be a string")
        else:
            try:
                re.compile(pattern)
            except re.error as exc:
                errors.append(f"{path}:invalid schema pattern:{exc}")
    return errors


def _schema_errors(value: Any, schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    if isinstance(value, float) and not math.isfinite(value):
        return [f"{path}:non_finite_number"]
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
        if "maxItems" in schema and len(value) > int(schema["maxItems"]):
            errors.append(f"{path}:maxItems violation")
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
        elif isinstance(schema.get("additionalProperties"), dict) and isinstance(properties, dict):
            additional_schema = schema["additionalProperties"]
            for field in sorted(set(value) - set(properties)):
                errors.extend(_schema_errors(value[field], additional_schema, f"{path}.{field}"))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}:minimum violation")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}:maximum violation")
    return errors


def validate_schema_document(value: Any, schema_path: Path) -> list[str]:
    if not schema_path.is_file():
        return [f"missing schema: {schema_path}"]
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid schema: {exc}"]
    definition_errors = _schema_definition_errors(schema, "schema")
    if definition_errors:
        return definition_errors
    return _schema_errors(value, schema, "document")


def _check_not_after_cutoff(
    value: Any,
    cutoff: datetime | None,
    label: str,
    errors: list[str],
) -> None:
    timestamp = parse_iso(value)
    if cutoff is not None and timestamp is not None and timestamp > cutoff:
        errors.append(f"{label}_after_cutoff")


def _evidence_reference_errors(
    value: Any,
    available_ids: set[str],
    path: str = "document",
    *,
    root: bool = True,
) -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if (key.endswith("evidence_ids") or key == "counterevidence_ids") and not (root and key == "evidence_ids") and isinstance(child, list):
                for index, evidence_id in enumerate(child):
                    if isinstance(evidence_id, str) and evidence_id not in available_ids:
                        errors.append(
                            f"{child_path}[{index}]:evidence_id_not_in_output_ledger:{evidence_id}"
                        )
            else:
                errors.extend(
                    _evidence_reference_errors(
                        child, available_ids, child_path, root=False
                    )
                )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(
                _evidence_reference_errors(
                    child, available_ids, f"{path}[{index}]", root=False
                )
            )
    return errors


def _integrity_errors(value: Any, cutoff: datetime | None, partition: str | None,
                      path: str = "document") -> list[str]:
    """Walk factual timestamps and provenance, not future forecasts/expiry dates."""
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            label = f"{path}.{key}"
            if key in {"as_of", "published_at", "known_at", "event_at", "assessment_as_of", "asserted_at"} and child is not None:
                stamp = parse_iso(child)
                if stamp is None:
                    errors.append(f"{label}:invalid_timestamp")
                elif cutoff is not None and stamp > cutoff:
                    errors.append(f"{label}:after_cutoff")
            if key in {"access_level", "source_partition"} and partition and child != partition:
                errors.append(f"{label}:partition_mismatch")
            errors.extend(_integrity_errors(child, cutoff, partition, label))
        state = value.get("evidence_state", value.get("verification_status", value.get("status")))
        if isinstance(state, str) and state in {"supported", "contradicted", "verified"} and "evidence_ids" in value and not value["evidence_ids"]:
            errors.append(f"{path}:evidenced_status_requires_evidence")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_integrity_errors(child, cutoff, partition, f"{path}[{index}]"))
    return errors


def validate_component(value: Any, schema_path: Path) -> list[str]:
    """Validate a v4 component and its cross-field safety invariants."""
    errors = validate_schema_document(value, schema_path)
    if not isinstance(value, dict):
        return errors
    if any(":type expected" in error for error in errors):
        return errors
    errors.extend(_integrity_errors(value, parse_iso(value.get("research_cutoff")), value.get("access_level")))
    name = schema_path.name
    if name == "bottleneck-assessment.schema.json":
        dimensions = value.get("dimensions")
        seen = [item.get("dimension") for item in dimensions if isinstance(item, dict)] if isinstance(dimensions, list) else []
        missing = sorted(BOTTLENECK_DIMENSIONS - set(seen))
        duplicates = sorted({item for item in seen if seen.count(item) > 1})
        errors.extend(f"bottleneck:missing_dimension:{item}" for item in missing)
        errors.extend(f"bottleneck:duplicate_dimension:{item}" for item in duplicates)
        cutoff = parse_iso(value.get("research_cutoff"))
        for index, dimension in enumerate(dimensions if isinstance(dimensions, list) else []):
            if isinstance(dimension, dict):
                _check_not_after_cutoff(
                    dimension.get("as_of"),
                    cutoff,
                    f"bottleneck:dimension_as_of:{index}",
                    errors,
                )
        capacity_states = value.get("capacity_states")
        capacity_seen = [item.get("state") for item in capacity_states if isinstance(item, dict)] if isinstance(capacity_states, list) else []
        capacity_missing = sorted(CAPACITY_STATES - set(capacity_seen))
        capacity_duplicates = sorted({item for item in capacity_seen if capacity_seen.count(item) > 1})
        errors.extend(f"bottleneck:missing_capacity_state:{item}" for item in capacity_missing)
        errors.extend(f"bottleneck:duplicate_capacity_state:{item}" for item in capacity_duplicates)
        edges = value.get("supply_chain_edges")
        edge_ids = [item.get("edge_id") for item in edges if isinstance(item, dict)] if isinstance(edges, list) else []
        if not edge_ids:
            errors.append("bottleneck:supply_chain_edge_required")
        errors.extend(
            f"bottleneck:duplicate_supply_chain_edge:{item}"
            for item in sorted({item for item in edge_ids if edge_ids.count(item) > 1})
        )
        for index, edge in enumerate(edges if isinstance(edges, list) else []):
            if not isinstance(edge, dict):
                continue
            _check_not_after_cutoff(edge.get("as_of"), cutoff, f"bottleneck:edge_as_of:{index}", errors)
            start = parse_iso(edge.get("effective_from"))
            end = parse_iso(edge.get("effective_to"))
            _check_not_after_cutoff(
                edge.get("effective_from"), cutoff, f"bottleneck:edge_effective_from:{index}", errors
            )
            _check_not_after_cutoff(
                edge.get("effective_to"), cutoff, f"bottleneck:edge_effective_to:{index}", errors
            )
            if start is not None and end is not None and end < start:
                errors.append(f"bottleneck:edge_effective_period_reversed:{index}")
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
        exposure = value.get("exposure_assessment")
        capture = value.get("capture_assessment")
        if isinstance(exposure, dict) and isinstance(capture, dict):
            if exposure.get("status") == "thematic_only" and capture.get("status") == "verified":
                errors.append("company:thematic_only_exposure_cannot_have_verified_capture")
        for section in (exposure, capture, value.get("capital_structure")):
            if isinstance(section, dict):
                _check_not_after_cutoff(
                    section.get("as_of"),
                    cutoff,
                    "company:nested_as_of",
                    errors,
                )
    elif name == "market-snapshot.schema.json":
        for field in ("price", "market_cap", "shares_outstanding"):
            number = value.get(field)
            if number is not None and (not finite_number(number) or number <= 0):
                errors.append(f"market:{field}_requires_positive_finite_number")
        if value.get("price") is not None and not value.get("price_source_evidence_ids"):
            errors.append("market:price_requires_source_evidence")
        if value.get("market_cap") is not None and not value.get("evidence_ids"):
            errors.append("market:market_cap_requires_source_evidence")
        if value.get("shares_outstanding") is not None and not value.get("shares_as_of"):
            errors.append("market:shares_require_as_of")
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
            expected_basis = "basic" if value.get("market_cap_basis") == "price_times_basic_shares" else "diluted"
            if value.get("shares_basis") != expected_basis:
                errors.append("market:calculated_market_cap_share_basis_mismatch")
            if value.get("quote_currency") != value.get("market_cap_currency"):
                errors.append("market:calculated_market_cap_currency_mismatch")
            operands = [value.get(key) for key in ("price", "shares_outstanding", "market_cap")]
            if all(finite_number(n) and n > 0 for n in operands):
                product = operands[0] * operands[1]
                if not finite_number(product) or not math.isclose(product, operands[2], rel_tol=0.001, abs_tol=0.01):
                    errors.append("market:calculated_market_cap_arithmetic_mismatch")
            if value.get("price_as_of") != value.get("market_cap_as_of"):
                errors.append("market:calculated_market_cap_price_time_mismatch")
        cutoff = parse_iso(value.get("research_cutoff"))
        for field in ("price_as_of", "market_cap_as_of", "shares_as_of"):
            timestamp = parse_iso(value.get(field))
            if cutoff is not None and timestamp is not None and timestamp > cutoff:
                errors.append(f"market:{field}_after_cutoff")
        price_time = parse_iso(value.get("price_as_of"))
        # A conservative ceiling, not an exchange-calendar freshness certification.
        if status in {"current", "delayed"} and cutoff and price_time and (cutoff - price_time).total_seconds() > 7 * 86400:
            errors.append("market:old_quote_cannot_be_current_or_delayed")
    elif name == "valuation-snapshot.schema.json":
        for field in ("market_cap", "enterprise_value"):
            number = value.get(field)
            if number is not None and (not finite_number(number) or (field == "market_cap" and number <= 0)):
                errors.append(f"valuation:{field}_invalid_numeric_value")
        for index, metric in enumerate(value.get("metrics", [])):
            number = metric.get("value") if isinstance(metric, dict) else None
            if number is not None and not finite_number(number):
                errors.append(f"valuation:metric:{index}:invalid_numeric_value")
    return errors


def validate_output(value: dict[str, Any], schema_root: Path) -> list[str]:
    schema_path = schema_root / "research-output.schema.json"
    errors: list[str] = []
    errors.extend(
        f"research_output:{error}"
        for error in validate_schema_document(value, schema_path)
    )
    if not isinstance(value, dict):
        return errors
    if any(":type expected" in error for error in errors):
        return errors
    errors.extend(_integrity_errors(value, parse_iso(value.get("research_cutoff")), value.get("access_level")))
    for key in ("bottleneck_assessment_ids", "company_profile_ids", "market_snapshot_ids", "valuation_snapshot_ids"):
        if not value.get(key):
            errors.append(f"research_output:required_component_ids:{key}")
    profiles = value.get("company_profile_ids")
    if not isinstance(profiles, list) or value.get("primary_candidate_id") not in profiles:
        errors.append("research_output:primary_candidate_not_in_company_profiles")

    method_application = value.get("method_application")
    if isinstance(method_application, dict):
        status = method_application.get("status")
        cards = method_application.get("cards", [])
        if status == "applied" and not cards:
            errors.append("research_output:applied_methods_require_cards")
        if status != "applied" and cards:
            errors.append("research_output:non_applied_method_status_cannot_list_cards")
        if isinstance(cards, list) and len(cards) > 6:
            errors.append("research_output:too_many_applied_method_cards")
        method_ids = [
            card.get("method_card_id")
            for card in cards
            if isinstance(card, dict) and isinstance(card.get("method_card_id"), str)
        ] if isinstance(cards, list) else []
        errors.extend(
            f"research_output:duplicate_method_card_id:{method_id}"
            for method_id in sorted({item for item in method_ids if method_ids.count(item) > 1})
        )
        for card_index, card in enumerate(cards if isinstance(cards, list) else []):
            if not isinstance(card, dict):
                continue
            if card.get("review_status") != "human_reviewed":
                errors.append(f"research_output:unreviewed_method_card_applied:{card_index}")
            questions = card.get("validation_questions", [])
            if not questions:
                errors.append(f"research_output:method_card_without_validation_question:{card_index}")
            for question_index, question in enumerate(questions if isinstance(questions, list) else []):
                if not isinstance(question, dict):
                    continue
                if question.get("verification_status") in {"supported", "contradicted"} and not question.get("evidence_ids"):
                    errors.append(
                        f"research_output:method_question_status_requires_evidence:{card_index}:{question_index}"
                    )

    timeline = value.get("historical_thesis_timeline")
    if isinstance(timeline, dict):
        timeline_status = timeline.get("status")
        event_ids = timeline.get("event_ids", [])
        if timeline_status == "events_found" and not event_ids:
            errors.append("research_output:events_found_requires_event_ids")
        if timeline_status != "events_found" and event_ids:
            errors.append("research_output:non_event_timeline_status_cannot_list_event_ids")
        if isinstance(event_ids, list) and len(event_ids) > 6:
            errors.append("research_output:too_many_timeline_events")

    available_evidence_ids = value.get("evidence_ids")
    if isinstance(available_evidence_ids, list):
        errors.extend(
            f"research_output:{error}"
            for error in _evidence_reference_errors(
                value, {item for item in available_evidence_ids if isinstance(item, str)}
            )
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

    ladder = value.get("validation_ladder")
    if isinstance(ladder, list):
        stages = [item.get("stage") for item in ladder if isinstance(item, dict)]
        missing = [stage for stage in VALIDATION_LADDER_STAGES if stage not in stages]
        duplicates = sorted({stage for stage in stages if stages.count(stage) > 1})
        errors.extend(f"research_output:validation_ladder_missing:{stage}" for stage in missing)
        errors.extend(f"research_output:validation_ladder_duplicate:{stage}" for stage in duplicates)
        if stages and stages[: len(VALIDATION_LADDER_STAGES)] != list(VALIDATION_LADDER_STAGES):
            errors.append("research_output:validation_ladder_order_invalid")
        if value.get("research_conclusion") == "supported":
            early = {
                item.get("stage"): item.get("status")
                for item in ladder
                if isinstance(item, dict)
            }
            for stage in VALIDATION_LADDER_STAGES[:5]:
                if early.get(stage) != "supported":
                    errors.append(f"research_output:supported_conclusion_requires_ladder_stage:{stage}")
        for item in ladder:
            if isinstance(item, dict) and item.get("status") == "supported" and item.get("missing_proof"):
                errors.append(f"research_output:supported_stage_has_missing_proof:{item.get('stage')}")

    reflexivity = value.get("reflexivity_check")
    if isinstance(reflexivity, dict):
        social_originated = reflexivity.get("social_originated") is True
        post_precedes = reflexivity.get("post_precedes_price_move") == "yes"
        independent = reflexivity.get("independent_fundamental_confirmation") == "yes"
        price_independent = reflexivity.get("price_action_is_independent_evidence") == "yes"
        if (social_originated or post_precedes) and not independent and price_independent:
            errors.append("research_output:reflexive_price_action_cannot_be_independent_without_fundamental_confirmation")
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
    print(f"OK: ResearchOutput structure {args.path.resolve()}; NOT an evidence audit. Run validate_research_bundle.py for linked-object checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
