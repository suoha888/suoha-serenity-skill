#!/usr/bin/env python3
"""Resolve a ResearchOutput against its local objects. Network-free, not a truth oracle.

Bundle keys: research_output, bottleneck_assessments, company_profiles,
market_snapshots, valuation_snapshots, claims, evidence, method_cards,
thesis_events, method_reviews. Arrays must contain complete schema objects.
Method reviews are separate, content-hash-bound human approval records.
Never export a bundle containing subscription/private material to a public repo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from validate_research_output import (
    _evidence_reference_errors, _integrity_errors, parse_iso,
    validate_component, validate_output, validate_schema_document,
)

REGISTRIES = {
    "bottleneck_assessments": ("bottleneck_id", "bottleneck-assessment"),
    "company_profiles": ("company_id", "company-profile"),
    "market_snapshots": ("snapshot_id", "market-snapshot"),
    "valuation_snapshots": ("valuation_id", "valuation-snapshot"),
    "claims": ("claim_id", "claim"),
    "evidence": ("evidence_id", "evidence"),
    "method_cards": ("method_id", "method-card"),
    "thesis_events": ("event_id", "thesis-event"),
}


def object_hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def validate_bundle(bundle: Any, schema_root: Path) -> list[str]:
    if not isinstance(bundle, dict) or not isinstance(bundle.get("research_output"), dict):
        return ["bundle:research_output_object_required"]
    output = bundle["research_output"]
    shape_errors = validate_schema_document(output, schema_root / "research-output.schema.json")
    if shape_errors:
        return [f"bundle:research_output:{error}" for error in shape_errors]
    errors = validate_output(output, schema_root)
    cutoff = parse_iso(output.get("research_cutoff"))
    partition = output.get("access_level")
    registries: dict[str, dict[str, dict]] = {}
    for collection, (id_key, schema) in REGISTRIES.items():
        rows = bundle.get(collection, [])
        registry: dict[str, dict] = {}
        registries[collection] = registry
        if not isinstance(rows, list):
            errors.append(f"bundle:{collection}:array_required")
            continue
        for index, row in enumerate(rows):
            prefix = f"bundle:{collection}:{index}"
            if not isinstance(row, dict):
                errors.append(f"{prefix}:object_required")
                continue
            row_errors = validate_schema_document(row, schema_root / f"{schema}.schema.json")
            if row_errors:
                errors.extend(f"{prefix}:{error}" for error in row_errors)
                continue
            errors.extend(f"{prefix}:{error}" for error in validate_component(row, schema_root / f"{schema}.schema.json"))
            errors.extend(_integrity_errors(row, cutoff, partition, prefix))
            identifier = row.get(id_key)
            if not isinstance(identifier, str) or not identifier:
                errors.append(f"{prefix}:id_required")
            elif identifier in registry:
                errors.append(f"{prefix}:duplicate_id:{identifier}")
            else:
                registry[identifier] = row
            if "research_cutoff" in row and parse_iso(row["research_cutoff"]) != cutoff:
                errors.append(f"{prefix}:cutoff_mismatch")

    links = {
        "bottleneck_assessment_ids": "bottleneck_assessments",
        "company_profile_ids": "company_profiles",
        "market_snapshot_ids": "market_snapshots",
        "valuation_snapshot_ids": "valuation_snapshots",
        "claim_ids": "claims", "evidence_ids": "evidence",
    }
    for key, collection in links.items():
        ids = output.get(key, [])
        if not isinstance(ids, list):
            continue
        for identifier in ids:
            if not isinstance(identifier, str) or identifier not in registries[collection]:
                errors.append(f"bundle:unresolved:{key}:{identifier}")
    evidence_ids = set(registries["evidence"])
    for collection, registry in registries.items():
        for identifier, row in registry.items():
            # A component's own ledger must resolve too, not just nested references.
            errors.extend(_evidence_reference_errors(row, evidence_ids, identifier, root=False))
            if collection in {"market_snapshots", "valuation_snapshots"}:
                company = registries["company_profiles"].get(row.get("company_id"))
                if company is None:
                    errors.append(f"bundle:{identifier}:company_not_found")
                elif collection == "market_snapshots":
                    for field in ("ticker", "exchange", "market", "quote_currency"):
                        if row.get(field) != company.get(field):
                            errors.append(f"bundle:{identifier}:issuer_mismatch:{field}")
            if collection == "company_profiles":
                for bottleneck in row.get("bottleneck_ids", []):
                    if bottleneck not in registries["bottleneck_assessments"]:
                        errors.append(f"bundle:{identifier}:bottleneck_not_found:{bottleneck}")
            if collection == "bottleneck_assessments":
                for company_id in row.get("candidate_company_ids", []):
                    if company_id not in registries["company_profiles"]:
                        errors.append(f"bundle:{identifier}:candidate_company_not_found:{company_id}")

    for identifier, item in registries["evidence"].items():
        for key in ("supports_claim_ids", "contradicts_claim_ids"):
            for claim_id in item.get(key, []):
                if claim_id not in registries["claims"]:
                    errors.append(f"bundle:{identifier}:claim_not_found:{claim_id}")
        known = parse_iso(item.get("known_at")) or parse_iso(item.get("published_at"))
        if known is None:
            errors.append(f"bundle:{identifier}:evidence_known_time_required")
        if item.get("review_status") == "rejected":
            errors.append(f"bundle:{identifier}:rejected_evidence")
        if not (item.get("content") or item.get("excerpt")):
            errors.append(f"bundle:{identifier}:evidence_content_or_excerpt_required")
    primary = output.get("primary_candidate_id")
    for collection, id_field in (("market_snapshots", "market_snapshot_ids"), ("valuation_snapshots", "valuation_snapshot_ids")):
        if not any(row.get("company_id") == primary and identifier in output.get(id_field, [])
                   for identifier, row in registries[collection].items()):
            errors.append(f"bundle:primary_candidate_missing:{collection}")
    # Confirmed operating rungs need a reviewed non-social source, not just a post.
    for stage in output.get("validation_ladder", []):
        if not isinstance(stage, dict) or stage.get("status") != "supported":
            continue
        sources = [registries["evidence"].get(eid, {}) for eid in stage.get("evidence_ids", [])]
        if not any(e.get("source_type") not in {"social_post", "local_archive"}
                   and e.get("evidence_grade") in {"primary", "strong_secondary"}
                   and e.get("review_status") == "human_reviewed" for e in sources):
            errors.append(f"bundle:{stage.get('stage')}:supported_stage_requires_reviewed_independent_evidence")

    reviews = bundle.get("method_reviews", [])
    if not isinstance(reviews, list):
        errors.append("bundle:method_reviews_array_required")
        reviews = []
    for applied in output.get("method_application", {}).get("cards", []):
        if not isinstance(applied, dict):
            continue
        method_id = applied.get("method_card_id")
        card = registries["method_cards"].get(method_id)
        if not card or card.get("review_status") != "human_reviewed":
            errors.append(f"bundle:unapproved_method:{method_id}")
            continue
        if applied.get("reasoning_pattern") != card.get("reasoning_pattern"):
            errors.append(f"bundle:method_pattern_mismatch:{method_id}")
        matching_reviews = [review for review in reviews if isinstance(review, dict) and review.get("method_id") == method_id
                       and review.get("reviewer")
                       and review.get("card_sha256") == object_hash(card)
                       and parse_iso(review.get("reviewed_at")) is not None
                       and cutoff is not None and parse_iso(review["reviewed_at"]) <= cutoff
                       ]
        matching_reviews.sort(key=lambda review: parse_iso(review["reviewed_at"]))
        approved = bool(matching_reviews and matching_reviews[-1].get("decision") == "approved")
        if not approved:
            errors.append(f"bundle:method_review_record_required:{method_id}")
        for claim_id in card.get("source_claim_ids", []):
            if claim_id not in registries["claims"]:
                errors.append(f"bundle:method_source_claim_missing:{claim_id}")
    for event_id in output.get("historical_thesis_timeline", {}).get("event_ids", []):
        event = registries["thesis_events"].get(event_id)
        if not event or event.get("review_status") != "human_reviewed":
            errors.append(f"bundle:unreviewed_or_missing_event:{event_id}")
    for event in registries["thesis_events"].values():
        for claim_id in event.get("claim_ids", []):
            if claim_id not in registries["claims"]:
                errors.append(f"bundle:event_claim_missing:{claim_id}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--schema-root", type=Path, default=Path(__file__).parents[1] / "schemas")
    args = parser.parse_args()
    try:
        errors = validate_bundle(json.loads(args.path.read_text(encoding="utf-8")), args.schema_root)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        errors = [f"bundle:invalid_input:{exc}"]
    for error in errors:
        print(f"ERROR: {error}")
    if not errors:
        print("OK: object links, partition and time checks passed; factual entailment still requires source review.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
