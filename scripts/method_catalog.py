#!/usr/bin/env python3
"""Inspect local candidate methods or select approved, hash-bound methods.

No model/API calls and no approval mutations. Decisions must come from a real
reviewer in <data-root>/reviews/<partition>/method-reviews.jsonl. Approval
records are integrity checks, not cryptographic proof of reviewer identity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_local_index import holdout_ids_for_partition, read_jsonl
from validate_research_bundle import object_hash
from validate_research_output import _integrity_errors, parse_iso, validate_schema_document


def catalog(data_root: Path, partition: str, cutoff: str, query: str = "", approved_only: bool = False) -> dict:
    if partition not in {"public", "subscription"}:
        raise ValueError("explicit public or subscription partition required")
    as_of = parse_iso(cutoff)
    if as_of is None:
        raise ValueError("timezone-aware cutoff required")
    card_path = data_root / "derived" / partition / "method-cards.jsonl"
    if not card_path.is_file():
        return {"status": "unavailable", "cards": []}
    holdout = holdout_ids_for_partition(data_root, partition)
    review_path = data_root / "reviews" / partition / "method-reviews.jsonl"
    reviews = list(read_jsonl(review_path)) if review_path.is_file() else []
    source_path = data_root / "normalized" / partition / "posts.jsonl"
    source_records = {str(row["id"]): row for row in read_jsonl(source_path)}
    result = []
    for card in read_jsonl(card_path):
        errors = validate_schema_document(card, Path(__file__).parents[1] / "schemas/method-card.schema.json")
        errors.extend(_integrity_errors(card, as_of, partition))
        if errors:
            raise ValueError(f"invalid method {card.get('method_id')}: {errors[0]}")
        ids = set(card["source_record_ids"])
        if not ids or ids.intersection(holdout):
            continue
        usable = True
        for identifier in ids:
            row = source_records.get(identifier, {})
            known = parse_iso(row.get("created_at"))
            if (not known or known > as_of or row.get("access_level") != partition
                    or row.get("source_partition") != partition
                    or row.get("provenance", {}).get("source_partition", partition) != partition):
                usable = False
                break
        if not usable:
            continue
        digest = object_hash(card)
        matching = [r for r in reviews if r.get("method_id") == card["method_id"]
                    and r.get("card_sha256") == digest and r.get("reviewer")
                    and parse_iso(r.get("reviewed_at")) is not None and parse_iso(r["reviewed_at"]) <= as_of]
        matching.sort(key=lambda r: parse_iso(r["reviewed_at"]))
        approval = bool(matching and matching[-1].get("decision") == "approved"
                        and card["review_status"] == "human_reviewed")
        if approved_only and not approval:
            continue
        searchable = " ".join([card["name"], card["problem"], card["reasoning_pattern"], *card["trigger_conditions"]]).casefold()
        if query and not any(token.casefold() in searchable for token in query.split()):
            continue
        result.append({"method_id": card["method_id"], "name": card["name"], "reasoning_pattern": card["reasoning_pattern"],
                       "works_when": card.get("works_when", card["trigger_conditions"]),
                       "fails_when": card.get("fails_when", card["known_failure_modes"]),
                       "required_evidence": card["required_evidence"], "counterexamples": card["counterexamples"],
                       "source_record_count": len(ids), "sample_source_record_ids": sorted(ids)[:3],
                       "review_status": card["review_status"], "approved": approval, "card_sha256": digest,
                       "access_level": partition})
    return {"status": "available" if result else "no_approved_match" if approved_only else "no_match",
            "partition": partition, "cutoff": cutoff, "cards": result,
            "note": "Candidates are heuristic templates with support links, not confirmed author-specific rules. Never auto-approve."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--partition", choices=["public", "subscription"], required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--query", default="")
    parser.add_argument("--approved-only", action="store_true")
    args = parser.parse_args()
    try:
        result = catalog(args.data_root, args.partition, args.as_of, args.query, args.approved_only)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
