#!/usr/bin/env python3
"""Deterministic checks for the Serenity Research Integrity P0 package.

The checks deliberately validate the contract between the skill instructions,
its structured research artifacts, and the small evaluation corpus. They do not
judge model prose or claim that a source is true.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_FILES = (
    "kernel/RESEARCH_KERNEL.md",
    "kernel/FINANCIAL_TRANSLATOR.md",
    "kernel/THESIS_TIMELINE.md",
    "contracts/output-contract.md",
    "contracts/provenance-contract.md",
    "contracts/temporal-contract.md",
    "contracts/access-control-contract.md",
    "contracts/company-research-contract.md",
    "schemas/claim.schema.json",
    "schemas/evidence.schema.json",
    "schemas/thesis.schema.json",
    "schemas/thesis-event.schema.json",
    "schemas/method-card.schema.json",
    "schemas/context-pack.schema.json",
    "schemas/relation.schema.json",
    "schemas/manifest.schema.json",
    "schemas/bottleneck-assessment.schema.json",
    "schemas/company-profile.schema.json",
    "schemas/market-snapshot.schema.json",
    "schemas/valuation-snapshot.schema.json",
    "schemas/research-output.schema.json",
    "schemas/normalized-post.schema.json",
    "adapters/ADAPTER_CONTRACT.md",
    "evals/README.md",
    "evals/golden.jsonl",
    "evals/temporal.jsonl",
    "evals/adversarial.jsonl",
    "evals/company-research.jsonl",
    "evals/fixtures/research-output.synthetic.json",
    "evals/fixtures/company-research-components.synthetic.json",
)

EXPECTED_SCHEMA_KEYS = {
    "schemas/claim.schema.json": {"claim_id", "epistemic_type", "evidence_state", "as_of"},
    "schemas/evidence.schema.json": {
        "evidence_id",
        "source",
        "published_at",
        "captured_at",
        "known_at",
        "content_hash",
        "provenance",
    },
    "schemas/thesis-event.schema.json": {
        "event_id",
        "thesis_id",
        "event_type",
        "event_at",
        "known_at",
        "claim_ids",
        "evidence_ids",
    },
    "schemas/normalized-post.schema.json": {
        "record_version",
        "id",
        "access_level",
        "source_partition",
        "text",
        "created_at",
        "captured_at",
        "time_status",
        "provenance",
        "record_hash",
    },
    "schemas/bottleneck-assessment.schema.json": {
        "bottleneck_id",
        "physical_mechanism",
        "dimensions",
        "capacity_states",
        "supply_chain_edges",
        "economic_capture_hypothesis",
        "research_cutoff",
    },
    "schemas/company-profile.schema.json": {
        "company_id",
        "legal_name",
        "ticker",
        "exchange",
        "quote_currency",
        "business_model",
        "financial_quality",
        "exposure_assessment",
        "capture_assessment",
        "capital_structure",
    },
    "schemas/market-snapshot.schema.json": {
        "snapshot_id",
        "price",
        "price_as_of",
        "market_cap",
        "market_cap_basis",
        "shares_outstanding",
        "shares_basis",
        "data_status",
    },
    "schemas/valuation-snapshot.schema.json": {
        "valuation_id",
        "expectation_gap",
        "scenario_bridges",
        "no_return_prediction",
        "no_trade_execution",
    },
    "schemas/research-output.schema.json": {
        "research_output_id",
        "research_cutoff",
        "market_snapshot_ids",
        "variant_perception",
        "conditional_reasons",
        "validation_ladder",
        "reflexivity_check",
        "no_return_prediction",
        "no_trade_execution",
    },
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def check_jsonl(path: Path, errors: list[str]) -> None:
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError as exc:
        errors.append(f"{path}: cannot read ({exc})")
        return
    if not lines:
        errors.append(f"{path}: must contain at least one JSONL case")
        return
    for line_no, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_no}: invalid JSON ({exc.msg})")
            continue
        if not isinstance(record, dict):
            errors.append(f"{path}:{line_no}: case must be a JSON object")
            continue
        for field in ("case_id", "task", "expected"):
            if field not in record:
                errors.append(f"{path}:{line_no}: missing {field}")


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    skill_path = root / "SKILL.md"
    if not skill_path.exists():
        errors.append(f"missing {skill_path}")
        return errors

    skill_text = skill_path.read_text(encoding="utf-8")
    required_terms = (
        "kernel/RESEARCH_KERNEL.md",
        "contracts/output-contract.md",
        "schemas/claim.schema.json",
        "research_cutoff",
        "UNKNOWN",
    )
    for term in required_terms:
        if term not in skill_text:
            errors.append(f"SKILL.md: missing integration reference or rule: {term}")

    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.exists():
            errors.append(f"missing {path}")

    for relative, expected_keys in EXPECTED_SCHEMA_KEYS.items():
        path = root / relative
        if not path.exists():
            continue
        try:
            schema = read_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: invalid schema ({exc})")
            continue
        if schema.get("type") != "object":
            errors.append(f"{path}: top-level type must be object")
        required = set(schema.get("required", []))
        missing = expected_keys - required
        if missing:
            errors.append(f"{path}: required fields missing: {', '.join(sorted(missing))}")

    for relative in ("evals/golden.jsonl", "evals/temporal.jsonl", "evals/adversarial.jsonl"):
        path = root / relative
        if path.exists():
            check_jsonl(path, errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).parents[1])
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAILED: {len(errors)} research-integrity checks")
        return 1
    print("OK: Research Integrity P0 contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
