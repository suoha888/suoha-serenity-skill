#!/usr/bin/env python3
"""Render a non-additive Serenity v4 research scorecard.

Usage:
  python scripts/serenity_scorecard.py --template
  python scripts/serenity_scorecard.py scorecard.json --format md
  cat scorecard.json | python scripts/serenity_scorecard.py - --format both

The command deliberately does not calculate a single conviction score. A
physical bottleneck, evidence quality, economic capture, valuation context,
catalyst timing, and risk are different questions and must remain visible.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Tuple


DIMENSIONS = (
    "architecture_necessity",
    "bottleneck_strength",
    "evidence_quality",
    "economic_value_capture",
    "financial_transmission",
    "valuation_context",
    "catalyst_timing",
    "reflexivity_risk",
    "risk",
)

LEGACY_FACTOR_MAP = {
    "architecture_necessity": ("architecture_coupling",),
    "bottleneck_strength": ("demand_inflection", "architecture_coupling", "chokepoint_severity", "supplier_concentration", "expansion_difficulty"),
    "evidence_quality": ("evidence_quality",),
    "economic_value_capture": ("demand_inflection", "architecture_coupling"),
    "financial_transmission": ("financial_transmission",),
    "valuation_context": ("valuation_disconnect",),
    "catalyst_timing": ("catalyst_timing",),
    "reflexivity_risk": ("reflexivity_risk", "social_reflexivity"),
}

TEMPLATE = {
    "scorecard_version": "4",
    "ticker": "EXAMPLE",
    "company": "Example Co",
    "market": "US/HK/A-share/Taiwan/Japan/Korea/Europe",
    "dimensions": {
        key: {"status": "unknown", "rating": None, "evidence_ids": [], "note": ""}
        for key in DIMENSIONS
    },
    "what_could_weaken_view": [""],
    "decision_rule": "Do not sum dimensions; rank only after the evidence gaps are visible.",
}


def _rating(value: Any, label: str) -> float | None:
    if value in (None, "", "unknown"):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number from 0 to 5 or null") from None
    if number < 0 or number > 5:
        raise ValueError(f"{label} must be from 0 to 5; got {number}")
    return number


def load_input(path: str) -> Dict[str, Any]:
    raw = sys.stdin.read() if path == "-" else open(path, "r", encoding="utf-8").read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("Input JSON must be an object")
    return data


def _legacy_dimensions(data: Dict[str, Any]) -> tuple[dict[str, Any], bool]:
    supplied = data.get("dimensions")
    if isinstance(supplied, dict):
        return supplied, False
    factors = data.get("factors")
    if not isinstance(factors, dict):
        return {}, False
    converted: dict[str, Any] = {}
    for dimension, legacy_keys in LEGACY_FACTOR_MAP.items():
        values = [factors.get(key) for key in legacy_keys if factors.get(key) is not None]
        converted[dimension] = {"rating": sum(float(value) for value in values) / len(values)} if values else {}
    penalties = data.get("penalties")
    if isinstance(penalties, dict):
        values = [float(value) for value in penalties.values() if value not in (None, "")]
        converted["risk"] = {"rating": sum(values) / len(values)} if values else {}
    return converted, True


def _priority(details: dict[str, dict[str, Any]]) -> str:
    architecture = details["architecture_necessity"].get("rating")
    bottleneck = details["bottleneck_strength"].get("rating")
    evidence = details["evidence_quality"].get("rating")
    capture = details["economic_value_capture"].get("rating")
    if all(value is not None and value >= 4 for value in (architecture, bottleneck, evidence, capture)):
        return "high"
    if all(value is not None and value >= 3 for value in (bottleneck, evidence)):
        return "medium"
    return "low"


def score(data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    dimensions, legacy = _legacy_dimensions(data)
    details: dict[str, dict[str, Any]] = {}
    for key in DIMENSIONS:
        raw = dimensions.get(key, {})
        if isinstance(raw, dict):
            value = raw.get("rating")
            note = str(raw.get("note") or "")
            evidence_ids = raw.get("evidence_ids", [])
        else:
            value = raw
            note = ""
            evidence_ids = []
        rating = _rating(value, f"dimensions.{key}.rating")
        details[key] = {
            "rating": rating,
            "status": "unknown" if rating is None else ("strong" if rating >= 4 else "mixed" if rating >= 2.5 else "weak"),
            "note": note,
            "evidence_ids": evidence_ids if isinstance(evidence_ids, list) else [],
        }
    priority = _priority(details)
    result = {
        "scorecard_version": "4",
        "ticker": data.get("ticker", ""),
        "company": data.get("company", ""),
        "market": data.get("market", ""),
        "dimensions": details,
        "research_priority": priority,
        "decision_rule": "Do not sum dimensions; resolve the largest evidence gap before ranking.",
        "legacy_input_detected": legacy,
        "kill_switches": data.get("what_could_weaken_view", data.get("kill_switches", [])),
        "evidence": data.get("evidence", []),
    }
    return result, priority


def to_markdown(result: Dict[str, Any]) -> str:
    title_bits = [result.get("ticker") or "Unknown"]
    if result.get("company"):
        title_bits.append(f"({result['company']})")
    title = " ".join(title_bits)
    lines = [
        f"# Research dimensions: {title}",
        "",
        f"Market: {result.get('market', '')}",
        f"Research priority: **{result['research_priority']}**",
        "",
        "No composite conviction score is calculated. Dimensions are separate:",
        "",
        "| Dimension | Status | Rating (0–5, optional) | Evidence | Note |",
        "|---|---|---:|---|---|",
    ]
    for key, detail in result["dimensions"].items():
        evidence = ", ".join(str(item) for item in detail.get("evidence_ids", []))
        note = detail.get("note", "").replace("|", "\\|")
        rating = "UNKNOWN" if detail.get("rating") is None else detail["rating"]
        lines.append(f"| {key} | {detail['status']} | {rating} | {evidence} | {note} |")

    weakening_items = [str(item).strip() for item in result.get("kill_switches", []) if str(item).strip()]
    if weakening_items:
        lines.extend(["", "## What could weaken the view"])
        lines.extend(f"- {item}" for item in weakening_items)
    lines.extend(["", "Decision rule: resolve the largest evidence gap before ranking the candidate.", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="JSON scorecard file, or '-' for stdin")
    parser.add_argument("--template", action="store_true", help="Print a JSON template")
    parser.add_argument("--format", choices=["json", "md", "both"], default="json")
    args = parser.parse_args()

    if args.template:
        print(json.dumps(TEMPLATE, ensure_ascii=False, indent=2))
        return
    if not args.input:
        parser.error("input is required unless --template is used")
    result, _ = score(load_input(args.input))
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.format == "md":
        print(to_markdown(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("\n---\n")
        print(to_markdown(result))


if __name__ == "__main__":
    main()
