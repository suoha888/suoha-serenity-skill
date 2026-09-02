#!/usr/bin/env python3
"""Deterministically distill normalized historical records into local layers.

This is a local, dependency-free candidate extractor.  It deliberately does
not call a model, read the raw archive, read outcomes, or make current-market
claims.  Its outputs are review queues and candidate method cards, not
authoritative judgments. A frozen temporal holdout is excluded by default.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


PIPELINE_VERSION = "2.0.0"
EXTRACTION_VERSION = "heuristic-2"
PARTITIONS = {"public", "subscription"}
EVENT_TYPES = {
    "establish",
    "reinforce",
    "weaken",
    "revise",
    "reverse",
    "invalidate",
    "close",
    "reopen",
    "risk_added",
    "catalyst_failed",
}

TICKER_RE = re.compile(r"\$([A-Z][A-Z0-9.-]{1,9})\b")
HANDLE_RE = re.compile(r"@([A-Za-z0-9_]{2,30})")
ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9.-]{1,8}\b")
SEGMENT_RE = re.compile(r"(?<=[.!?。！？])\s+|\n+")
COMMON_ACRONYMS = {
    "AI",
    "API",
    "ASP",
    "CPO",
    "CPU",
    "GPU",
    "HBM",
    "IR",
    "LTA",
    "OEM",
    "ROI",
    "SEC",
    "SOX",
    "US",
    "UK",
}

METHODS: dict[str, dict[str, Any]] = {
    "chain_first": {
        "name": "Chain-first mapping",
        "keywords": (
            "supply chain",
            "value chain",
            "产业链",
            "供应链",
            "upstream",
            "downstream",
            "component",
            "supplier",
            "bottleneck",
            "卡点",
            "瓶颈",
        ),
        "problem": "A popular narrative hides where the system actually depends on scarce supply.",
        "trigger_conditions": ["A downstream theme is broad or crowded.", "The user starts with a ticker or headline."],
        "reasoning_pattern": "Translate demand into system change, walk from downstream to upstream, and rank layers before companies.",
        "required_evidence": ["system architecture", "supplier or process evidence", "customer or capacity evidence"],
        "disconfirming_evidence": ["easy substitution", "many interchangeable suppliers", "no observable demand transmission"],
        "known_failure_modes": ["mistaking a named supplier for a constrained supplier", "drawing edges from a single social post"],
    },
    "physical_constraint": {
        "name": "Physical constraint first",
        "keywords": (
            "capacity",
            "yield",
            "qualification",
            "lead time",
            "purity",
            "wafer",
            "power",
            "thermal",
            "latency",
            "bandwidth",
            "扩产",
            "认证",
            "良率",
        ),
        "problem": "Narrative excitement is not the same as a hard-to-scale constraint.",
        "trigger_conditions": ["Demand is growing faster than a physical or qualification process can scale."],
        "reasoning_pattern": "Test scarcity, substitutability, qualification time, and expansion lead time before naming a beneficiary.",
        "required_evidence": ["capacity", "lead time", "qualification", "supplier concentration"],
        "disconfirming_evidence": ["validated substitutes", "rapid competitor expansion", "unconstrained capacity"],
        "known_failure_modes": ["confusing temporary commentary with structural scarcity", "ignoring customer qualification"],
    },
    "evidence_convergence": {
        "name": "Evidence convergence",
        "keywords": (
            "filing",
            "earnings",
            "transcript",
            "customer",
            "order",
            "公告",
            "财报",
            "电话会",
            "客户",
            "订单",
            "evidence",
            "证据",
        ),
        "problem": "One source can be wrong, promotional, stale, or copied by many outlets.",
        "trigger_conditions": ["A material claim is important enough to change ranking or confidence."],
        "reasoning_pattern": "Triangulate independent primary and secondary sources and collapse copied reports into one lineage.",
        "required_evidence": ["primary source", "independence group", "date and locator"],
        "disconfirming_evidence": ["contradictory filing", "source dependency", "unverifiable customer claim"],
        "known_failure_modes": ["counting five rewrites as five independent confirmations", "using an inaccessible citation"],
    },
    "economic_transmission": {
        "name": "Constraint to economics",
        "keywords": (
            "revenue",
            "margin",
            "gross profit",
            "cash flow",
            "capex",
            "pricing",
            "price",
            "收入",
            "毛利",
            "现金流",
            "资本开支",
            "价格",
        ),
        "problem": "A bottleneck may be real without creating economic capture for the company.",
        "trigger_conditions": ["A scarce layer has been identified.", "The user asks who benefits financially."],
        "reasoning_pattern": "Trace scarcity through pricing, orders, mix, margin, cash flow, funding, and dilution.",
        "required_evidence": ["segment disclosure", "orders or pricing", "margin or cash-flow bridge"],
        "disconfirming_evidence": ["no economic capture", "customer power absorbs value", "funding overwhelms operating gains"],
        "known_failure_modes": ["treating revenue growth as proof of pricing power", "ignoring dilution and working capital"],
    },
    "falsification_first": {
        "name": "Falsification-first planning",
        "keywords": (
            "wrong",
            "risk",
            "downgrade",
            "contradict",
            "invalidate",
            "weak",
            "失效",
            "风险",
            "降级",
            "反方",
            "错误",
        ),
        "problem": "A compelling thesis can survive indefinitely unless its failure conditions are explicit.",
        "trigger_conditions": ["A thesis is being ranked, strengthened, or updated."],
        "reasoning_pattern": "Name the strongest alternative explanation and the three observations that would downgrade the view.",
        "required_evidence": ["alternative thesis", "observable failure condition", "dated follow-up check"],
        "disconfirming_evidence": ["demand delay", "substitution", "qualification failure", "execution miss"],
        "known_failure_modes": ["performative risk paragraphs with no measurable check", "calling a thesis invalidated from one weak signal"],
    },
    "temporal_replay": {
        "name": "As-of thesis replay",
        "keywords": (
            "update",
            "previously",
            "now",
            "before",
            "later",
            "timeline",
            "当时",
            "后来",
            "更新",
            "之前",
            "时间",
        ),
        "problem": "Later knowledge can silently rewrite what was knowable at the time.",
        "trigger_conditions": ["The question is historical or a thesis has changed over time."],
        "reasoning_pattern": "Freeze a cutoff, filter on known_at, and represent belief changes as dated events.",
        "required_evidence": ["published_at", "known_at", "as_of", "event trigger"],
        "disconfirming_evidence": ["future source used in replay", "outcome label leaking into research context"],
        "known_failure_modes": ["using import time as public availability", "upgrading method quality because price later rose"],
    },
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_id(prefix: str, *parts: Any) -> str:
    payload = stable_json(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:20]}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: record must be an object")
            records.append(value)
    return records


def write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(stable_json(dict(record)) + "\n")
            count += 1
    return count


def unique_lineage(records: Iterable[Mapping[str, Any]], partition: str) -> list[dict[str, str]]:
    result: dict[tuple[str, str], dict[str, str]] = {}
    for record in records:
        provenance = record.get("provenance")
        if not isinstance(provenance, Mapping):
            raise ValueError(f"record {record.get('id')} has no provenance")
        source_file = str(provenance.get("source_file") or "")
        source_record_id = str(provenance.get("source_record_id") or record.get("id") or "")
        source_sha256 = str(provenance.get("source_sha256") or "")
        if not source_file or not source_record_id or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
            raise ValueError(f"record {record.get('id')} has incomplete source lineage")
        if str(record.get("access_level")) != partition or str(record.get("source_partition")) != partition:
            raise ValueError(f"record {record.get('id')} violates {partition} partition")
        key = (source_file, source_record_id)
        result[key] = {
            "source_partition": partition,
            "source_file": source_file,
            "source_record_id": source_record_id,
            "source_sha256": source_sha256,
        }
    return [result[key] for key in sorted(result)]


def record_time(record: Mapping[str, Any]) -> datetime | None:
    return parse_timestamp(record.get("created_at")) or parse_timestamp(record.get("captured_at"))


def split_segments(text: str) -> list[str]:
    pieces = [piece.strip() for piece in SEGMENT_RE.split(text or "") if piece.strip()]
    if not pieces and text.strip():
        pieces = [text.strip()]
    return pieces[:50]


def classify_segment(text: str) -> str:
    lower = text.lower()
    if any(marker in lower for marker in ("unknown", "unclear", "not sure", "不知道", "无法确认", "尚不清楚")):
        return "unknown"
    if any(marker in lower for marker in ("may ", "might ", "could ", "likely", "perhaps", "maybe", "可能", "或许", "大概率", "我认为")):
        return "hypothesis"
    if any(marker in lower for marker in ("therefore", "means", "implies", "suggests", "意味着", "因此", "说明", "推断")):
        return "inference"
    if any(marker in lower for marker in ("announced", "reported", "filed", "according to", "公告", "披露", "财报显示", "宣布")):
        return "fact"
    return "unknown"


def extract_entity_tokens(text: str) -> list[str]:
    tokens: set[str] = set()
    tokens.update("$" + match.upper() for match in TICKER_RE.findall(text))
    tokens.update("@" + match for match in HANDLE_RE.findall(text))
    for match in ACRONYM_RE.findall(text):
        if match not in COMMON_ACRONYMS and len(match) >= 3:
            tokens.add(match)
    return sorted(tokens)


def entity_id(token: str) -> str:
    return stable_id("entity", token.lower())


def event_type_for(text: str) -> str | None:
    lower = text.lower()
    if any(marker in lower for marker in ("invalidate", "thesis is dead", "彻底失效", "证明错误")):
        return "invalidate"
    if any(marker in lower for marker in ("reverse", "reversed", "反转", "反过来")):
        return "reverse"
    if any(marker in lower for marker in ("reopen", "重新打开", "重新看")):
        return "reopen"
    if any(marker in lower for marker in ("downgrade", "weaken", "weakens", "降级", "削弱", "走弱")):
        return "weaken"
    if any(marker in lower for marker in ("revise", "revised", "update", "更新", "调整", "修正")):
        return "revise"
    if any(marker in lower for marker in ("risk", "风险", "concern", "担忧")):
        return "risk_added"
    if any(marker in lower for marker in ("catalyst failed", "催化失败", "没有兑现")):
        return "catalyst_failed"
    if any(marker in lower for marker in ("new evidence", "still", "reinforce", "强化", "继续验证", "新证据")):
        return "reinforce"
    if any(marker in lower for marker in ("thesis", "观点", "逻辑", "bottleneck", "瓶颈")):
        return "establish"
    return None


def context_packs(records: list[dict[str, Any]], partition: str, cutoff: datetime | None) -> list[dict[str, Any]]:
    usable: list[dict[str, Any]] = []
    for record in records:
        if str(record.get("access_level")) != partition:
            raise ValueError(f"record {record.get('id')} has inconsistent access level")
        if cutoff is not None:
            known = parse_timestamp(record.get("created_at"))
            if known is None or known > cutoff:
                continue
        usable.append(record)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in usable:
        key = str(record.get("conversation_id") or record.get("id"))
        groups[key].append(record)
    packs: list[dict[str, Any]] = []
    for key, group in sorted(groups.items()):
        group.sort(key=lambda row: (record_time(row) or datetime.max.replace(tzinfo=timezone.utc), str(row.get("id"))))
        ids = {str(row.get("id")) for row in group}
        root = next((row for row in group if not row.get("parent_id")), group[0])
        missing_parent = any(row.get("parent_id") and str(row.get("parent_id")) not in ids for row in group)
        if missing_parent:
            completeness = "partial"
        elif any(row.get("is_reply") and not row.get("parent_id") for row in group):
            completeness = "missing"
        else:
            completeness = "complete"
        media_refs: list[dict[str, Any]] = []
        for row in group:
            for media in row.get("media") or []:
                if not isinstance(media, Mapping):
                    continue
                local_ref = str(media.get("local_path") or media.get("path") or "")
                media_type = str(media.get("type") or "unknown").lower()
                media_refs.append(
                    {
                        "media_id": stable_id("media", partition, row.get("id"), local_ref, media_type),
                        "post_id": str(row.get("id")),
                        "media_type": media_type,
                        "local_ref": local_ref,
                        "access_level": partition,
                        "extraction_status": "triage_only",
                    }
                )
        lineage = unique_lineage(group, partition)
        created_times = [parse_timestamp(row.get("created_at")) for row in group]
        created_times = [value for value in created_times if value is not None]
        pack_records = [
            {
                "id": str(row.get("id")),
                "text": str(row.get("text") or ""),
                "created_at": row.get("created_at"),
                "created_at_raw": row.get("created_at_raw"),
                "captured_at": row.get("captured_at"),
                "parent_id": row.get("parent_id"),
                "is_reply": bool(row.get("is_reply")),
                "is_quote": bool(row.get("is_quote")),
                "quote_status": row.get("quote_status"),
                "url": row.get("url"),
                "entity_tokens": extract_entity_tokens(str(row.get("text") or "")),
            }
            for row in group
        ]
        packs.append(
            {
                "schema_version": "2",
                "context_id": stable_id("context", partition, key, [str(row.get("id")) for row in group]),
                "root_post_id": str(root.get("id")),
                "conversation_id": root.get("conversation_id"),
                "record_ids": [str(row.get("id")) for row in group],
                "records": pack_records,
                "context_completeness": completeness,
                "context_missing": completeness != "complete",
                "media_refs": media_refs,
                "max_source_created_at": iso(max(created_times) if created_times else None),
                "access_level": partition,
                "source_partition": partition,
                "source_lineage": lineage,
                "extraction_version": EXTRACTION_VERSION,
            }
        )
    return packs


def distill(records: list[dict[str, Any]], partition: str, cutoff: datetime | None, min_support: int) -> dict[str, list[dict[str, Any]]]:
    packs = context_packs(records, partition, cutoff)
    claims: list[dict[str, Any]] = []
    evidence: dict[str, dict[str, Any]] = {}
    entities: dict[str, dict[str, Any]] = {}
    relations: list[dict[str, Any]] = []
    thesis_events: list[dict[str, Any]] = []
    theses: dict[str, dict[str, Any]] = {}
    method_support: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"packs": set(), "claims": set(), "events": set()})
    media_triage: list[dict[str, Any]] = []

    for pack in packs:
        pack_records = pack["records"]
        source_records = [record for record in records if str(record.get("id")) in set(pack["record_ids"])]
        lineage = pack["source_lineage"]
        pack_text = "\n".join(str(row.get("text") or "") for row in pack_records)
        pack_entities = extract_entity_tokens(pack_text)
        for token in pack_entities:
            eid = entity_id(token)
            entities[eid] = {
                "schema_version": "2",
                "entity_id": eid,
                "label": token,
                "entity_type": "ticker_or_mention",
                "access_level": partition,
                "source_partition": partition,
                "source_record_ids": pack["record_ids"],
                "source_lineage": lineage,
                "review_status": "pending",
                "extraction_version": EXTRACTION_VERSION,
            }
        for media in pack["media_refs"]:
            media_triage.append(
                {
                    "schema_version": "2",
                    "media_id": media["media_id"],
                    "post_id": media["post_id"],
                    "media_type": media["media_type"],
                    "contains_text": media["media_type"] in {"chart", "table", "screenshot", "diagram"},
                    "extraction_status": "triage_only",
                    "recommended_next_step": "local_vision_review" if media["media_type"] in {"chart", "table", "screenshot", "diagram"} else "not_needed",
                    "local_ref": media["local_ref"],
                    "access_level": partition,
                    "source_partition": partition,
                    "source_record_ids": [media["post_id"]],
                    "source_lineage": lineage,
                    "review_status": "pending",
                    "extraction_version": EXTRACTION_VERSION,
                }
            )
        for row in pack_records:
            record_id = str(row["id"])
            source = next(item for item in source_records if str(item.get("id")) == record_id)
            evidence_id = stable_id("evidence", partition, record_id, source.get("record_hash"))
            source_url = str(source.get("url") or f"local://{partition}/{record_id}")
            evidence[evidence_id] = {
                "schema_version": "2",
                "evidence_id": evidence_id,
                "source": source_url,
                "source_type": "social_post",
                "content": str(source.get("text") or ""),
                "excerpt": str(source.get("text") or "")[:500],
                "published_at": source.get("created_at"),
                "captured_at": source.get("captured_at"),
                "known_at": source.get("created_at"),
                "locator": source_url,
                "content_hash": str(source.get("record_hash") or ""),
                "provenance": {
                    "adapter": "historical-normalized",
                    "locator": f"{source.get('provenance', {}).get('source_file')}#{record_id}",
                    "extraction_version": EXTRACTION_VERSION,
                    "human_reviewed": False,
                },
                "access_level": partition,
                "source_partition": partition,
                "source_record_ids": [record_id],
                "source_lineage": unique_lineage([source], partition),
                "evidence_grade": "lead",
                "primary_or_secondary": "secondary",
                "independence_group": f"social-post:{record_id}",
                "supports_claim_ids": [],
                "contradicts_claim_ids": [],
                "review_status": "pending",
                "metadata": {"post_id": record_id, "context_id": pack["context_id"]},
            }
            for relation_type, target in (("reply_to", source.get("parent_id")), ("quotes", source.get("quote_of"))):
                if target:
                    relations.append(
                        {
                            "schema_version": "2",
                            "relation_id": stable_id("relation", partition, record_id, relation_type, target),
                            "source_id": record_id,
                            "relation_type": relation_type,
                            "target_id": str(target),
                            "as_of": source.get("created_at"),
                            "access_level": partition,
                            "source_partition": partition,
                            "source_record_ids": [record_id],
                            "source_lineage": unique_lineage([source], partition),
                            "review_status": "pending",
                            "extraction_version": EXTRACTION_VERSION,
                        }
                    )
            segments = split_segments(str(source.get("text") or ""))
            for segment_index, segment in enumerate(segments):
                if len(segment) < 12:
                    continue
                segment_entities = [entity_id(token) for token in extract_entity_tokens(segment)]
                claim_id = stable_id("claim", partition, record_id, segment_index, segment)
                claim_as_of = cutoff or parse_timestamp(source.get("created_at")) or parse_timestamp(source.get("captured_at"))
                if claim_as_of is None:
                    continue
                claims.append(
                    {
                        "schema_version": "2",
                        "claim_id": claim_id,
                        "text": segment,
                        "epistemic_type": classify_segment(segment),
                        "entity_ids": segment_entities,
                        "as_of": iso(claim_as_of),
                        "asserted_at": source.get("created_at"),
                        "known_at": source.get("created_at"),
                        "evidence_ids": [evidence_id],
                        "counterevidence_ids": [],
                        "evidence_state": "not_established",
                        "confidence": "low",
                        "access_level": partition,
                        "source_partition": partition,
                        "source_record_ids": [record_id],
                        "source_lineage": unique_lineage([source], partition),
                        "review_status": "pending",
                        "extraction_version": EXTRACTION_VERSION,
                        "notes": "Heuristic candidate extracted from a social lead; external verification is required.",
                    }
                )
                evidence[evidence_id]["supports_claim_ids"].append(claim_id)
                for token in extract_entity_tokens(segment):
                    relations.append(
                        {
                            "schema_version": "2",
                            "relation_id": stable_id("relation", partition, record_id, "mentions", token, segment_index),
                            "source_id": record_id,
                            "relation_type": "mentions",
                            "target_id": entity_id(token),
                            "as_of": source.get("created_at"),
                            "access_level": partition,
                            "source_partition": partition,
                            "source_record_ids": [record_id],
                            "source_lineage": unique_lineage([source], partition),
                            "review_status": "pending",
                            "extraction_version": EXTRACTION_VERSION,
                        }
                    )
        event_kind = event_type_for(pack_text)
        event_claims = [claim for claim in claims if set(claim["source_record_ids"]).intersection(pack["record_ids"])]
        if event_kind and event_kind in EVENT_TYPES and event_claims:
            event_id = stable_id("event", partition, pack["context_id"], event_kind)
            thesis_id = stable_id("thesis", partition, pack_entities or [pack["context_id"]])
            event_at = pack.get("max_source_created_at")
            before_after = {
                "establish": ("candidate", "forming"),
                "reinforce": ("forming", "supported"),
                "weaken": ("supported", "weakened"),
                "revise": ("supported", "revised"),
                "reverse": ("supported", "revised"),
                "invalidate": ("revised", "invalidated"),
                "close": ("supported", "closed"),
                "reopen": ("closed", "forming"),
                "risk_added": ("supported", "weakened"),
                "catalyst_failed": ("supported", "weakened"),
            }[event_kind]
            event = {
                "schema_version": "2",
                "event_id": event_id,
                "thesis_id": thesis_id,
                "event_type": event_kind,
                "event_at": event_at,
                "known_at": event_at,
                "claim_ids": [claim["claim_id"] for claim in event_claims],
                "evidence_ids": sorted({evidence_id for claim in event_claims for evidence_id in claim["evidence_ids"]}),
                "before": before_after[0],
                "after": before_after[1],
                "reason": "Heuristic event candidate; confirm the state transition and trigger evidence during human review.",
                "access_level": partition,
                "source_partition": partition,
                "source_record_ids": pack["record_ids"],
                "source_lineage": lineage,
                "review_status": "pending",
                "extraction_version": EXTRACTION_VERSION,
            }
            thesis_events.append(event)
            method_support["temporal_replay"]["events"].add(event_id)
            theses[thesis_id] = {
                "schema_version": "2",
                "thesis_id": thesis_id,
                "topic": ", ".join(pack_entities),
                "statement": pack_text[:500],
                "causal_chain": ["source context", "candidate mechanism", "required evidence"],
                "bottleneck": "UNKNOWN until independently verified",
                "assumptions": ["The extracted context is complete enough to interpret."],
                "failure_conditions": ["Independent evidence contradicts the mechanism.", "The relevant constraint proves substitutable."],
                "state": before_after[1],
                "confidence": "low",
                "opened_at": event_at,
                "last_updated_at": event_at,
                "access_level": partition,
                "source_partition": partition,
                "source_record_ids": pack["record_ids"],
                "source_lineage": lineage,
                "review_status": "pending",
                "extraction_version": EXTRACTION_VERSION,
            }
        for method_key, definition in METHODS.items():
            if any(keyword.lower() in pack_text.lower() for keyword in definition["keywords"]):
                method_support[method_key]["packs"].add(pack["context_id"])
                method_support[method_key]["claims"].update(
                    claim["claim_id"] for claim in event_claims
                )

    method_cards: list[dict[str, Any]] = []
    for method_key, support in sorted(method_support.items()):
        if len(support["packs"]) < min_support:
            continue
        definition = METHODS[method_key]
        selected_packs = [pack for pack in packs if pack["context_id"] in support["packs"]]
        selected_ids = sorted({record_id for pack in selected_packs for record_id in pack["record_ids"]})
        lineage = unique_lineage(
            [record for record in records if str(record.get("id")) in set(selected_ids)],
            partition,
        )
        card_id = stable_id("method", partition, method_key, sorted(support["packs"]))
        method_cards.append(
            {
                "schema_version": "2",
                "method_id": card_id,
                "name": definition["name"],
                "problem": definition["problem"],
                "trigger_conditions": list(definition["trigger_conditions"]),
                "reasoning_pattern": definition["reasoning_pattern"],
                "required_evidence": list(definition["required_evidence"]),
                "disconfirming_evidence": list(definition["disconfirming_evidence"]),
                "known_failure_modes": list(definition["known_failure_modes"]),
                "counterexamples": ["A repeated social narrative can be wrong even when it is internally coherent."],
                "source_event_ids": sorted(support["events"]),
                "source_claim_ids": sorted(support["claims"]),
                "confidence": "low",
                "access_level": partition,
                "source_partition": partition,
                "source_record_ids": selected_ids,
                "source_lineage": lineage,
                "review_status": "candidate",
                "extraction_version": EXTRACTION_VERSION,
            }
        )
    for record in evidence.values():
        record["supports_claim_ids"] = sorted(set(record["supports_claim_ids"]))
    return {
        "context-packs.jsonl": packs,
        "entities.jsonl": sorted(entities.values(), key=lambda row: row["entity_id"]),
        "claims.jsonl": claims,
        "evidence.jsonl": sorted(evidence.values(), key=lambda row: row["evidence_id"]),
        "relations.jsonl": relations,
        "theses.jsonl": sorted(theses.values(), key=lambda row: row["thesis_id"]),
        "thesis-events.jsonl": thesis_events,
        "method-cards.jsonl": method_cards,
        "media-triage.jsonl": media_triage,
    }


def run(
    input_path: Path,
    output_root: Path,
    partition: str,
    cutoff: datetime | None,
    min_support: int,
    replace: bool,
    exclude_record_ids: set[str] | None = None,
) -> dict[str, Any]:
    if partition not in PARTITIONS:
        raise ValueError(f"partition must be one of {sorted(PARTITIONS)}")
    input_path = input_path.resolve()
    output_root = output_root.resolve()
    if output_root.name != partition:
        raise ValueError(
            "output_root must end with the selected partition name "
            f"({partition}); omit --output-root or use .../derived/{partition}"
        )
    if output_root == input_path or output_root in input_path.parents:
        raise ValueError("output_root cannot replace the normalized input path")
    all_records = read_jsonl(input_path)
    excluded = {str(value) for value in (exclude_record_ids or set())}
    all_ids = {str(record.get("id")) for record in all_records}
    unknown_excluded = sorted(excluded - all_ids)
    if unknown_excluded:
        raise ValueError(
            "holdout contains IDs missing from normalized input: "
            + ", ".join(unknown_excluded[:5])
        )
    records = [record for record in all_records if str(record.get("id")) not in excluded]
    layers = distill(records, partition, cutoff, min_support)
    if output_root.exists() and not replace:
        raise FileExistsError(f"output exists; pass --replace to regenerate: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{partition}.distill-", dir=str(output_root.parent)))
    try:
        counts: dict[str, int] = {}
        for filename, rows in layers.items():
            counts[filename] = write_jsonl(staging / filename, rows)
        manifest = {
            "manifest_version": "2",
            "pipeline_version": PIPELINE_VERSION,
            "created_at": utc_now_iso(),
            "input": {
                "path": input_path.as_posix(),
                "sha256": sha256_file(input_path),
                "record_count": len(records),
                "source_record_count": len(all_records),
            },
            "partition": partition,
            "cutoff": iso(cutoff),
            "counts": counts,
            "output_files": {filename: {"count": count} for filename, count in counts.items()},
            "raw_archive_read": False,
            "outcomes_read": False,
            "access_policy": "taint-preserving",
            "holdout_excluded": bool(excluded),
            "excluded_holdout_count": len(excluded),
            "notes": "Heuristic candidate extraction; human review is required before treating method cards as reusable.",
        }
        (staging / "distillation-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if output_root.exists():
            shutil.rmtree(output_root)
        staging.replace(output_root)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


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
    rows = read_jsonl(holdout_path)
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--data-root", type=Path, default=Path("data/serenity"))
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--partition", choices=sorted(PARTITIONS), required=True)
    parser.add_argument("--cutoff")
    parser.add_argument("--min-support", type=int, default=3)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument(
        "--include-holdout",
        action="store_true",
        help="explicit evaluator-only override; release distillations exclude the frozen holdout by default",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        cutoff = parse_timestamp(args.cutoff) if args.cutoff else None
        if args.cutoff and cutoff is None:
            raise ValueError("cutoff must be a timezone-aware ISO timestamp")
        input_path = args.input or args.data_root / "normalized" / args.partition / "posts.jsonl"
        output_root = args.output_root or args.data_root / "derived" / args.partition
        excluded_ids: set[str] = set()
        holdout_manifest = args.data_root / "holdout" / "temporal-holdout-manifest.json"
        if holdout_manifest.is_file() and not args.include_holdout:
            excluded_ids = holdout_ids_for_partition(args.data_root, args.partition)
        manifest = run(
            input_path,
            output_root,
            args.partition,
            cutoff,
            max(1, args.min_support),
            args.replace,
            exclude_record_ids=excluded_ids,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"OK: distilled {manifest['partition']} ({manifest['input']['record_count']} records)")
        print(json.dumps(manifest["counts"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
