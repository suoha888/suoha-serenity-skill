#!/usr/bin/env python3
"""Serenity Lens engine (v6): compute scenario math and validate a SerenityLens.

Network-free and dependency-free.  Subcommands:

  compute   Fill derived numbers (market cap, implied market cap, per-share,
            vs-current %, TAM ratios) from the raw assumptions so the agent
            never hand-types derived arithmetic.
  validate  Enforce the contract: schema, arithmetic, freshness, evidence
            links, cutoff discipline, tier gating, red-team/falsification
            completeness, memory hygiene, and the advice boundary.  Lenses
            with schema_version "6.0" must also carry the doctrine block
            (live data, framework fit, bottleneck status, phase, purity,
            risk tier, variant perception, next-hop picks).
  finish    One step for delivery: refuse unfilled TODO fields, compute,
            validate, render Markdown/HTML, and verify the rendered files.

The framework is distilled from Serenity's public posts for research and
backtesting; lenses never speak for Serenity and are not investment advice.

Scenario valuations are hypotheses that show what must be true; they are not
price targets, return forecasts, or trade instructions.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_research_output import parse_iso, validate_schema_document  # noqa: E402

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "serenity-lens.schema.json"
TOLERANCE = 0.01  # 1% relative tolerance for recomputed arithmetic
MAX_PRICE_AGE_DAYS = 7
MAX_SHARES_AGE_DAYS = 200
SCENARIO_ORDER = ("bear", "base", "bull")
PLAYBOOK_PATH = Path(__file__).resolve().parents[1] / "references" / "serenity-playbook.md"
DOCTRINE_PATH = Path(__file__).resolve().parents[1] / "references" / "serenity-doctrine.md"
RULE_ID_RE = re.compile(r"\b((?:PB|ARC)-[A-Z0-9]+(?:-[A-Z0-9]+)*)\b")


def playbook_ids(path: Path | None = None) -> set[str]:
    """Rule (PB-*) and archetype (ARC-*) IDs defined in the playbook (v5) and
    the doctrine (v6).  Passing an explicit path reads only that file."""
    paths = [path] if path is not None else [PLAYBOOK_PATH, DOCTRINE_PATH]
    ids: set[str] = set()
    for p in paths:
        if p.exists():
            ids.update(RULE_ID_RE.findall(p.read_text(encoding="utf-8")))
    return ids


V6_REQUIRED = (
    "live_data", "framework_fit", "bottleneck_status", "phase", "purity",
    "risk_tier", "variant_perception", "next_hop_picks",
)

# Keys that would turn research into an execution instruction.
FORBIDDEN_KEYS = {
    "position_size", "position_sizing", "allocation_pct", "portfolio_weight",
    "order", "orders", "buy_now", "sell_now", "entry_price_instruction",
    "price_target", "target_price", "expected_return", "win_probability",
    "leverage_advice", "guaranteed_return",
}
FORBIDDEN_PHRASES = re.compile(
    r"(建议买入|建议卖出|立即买入|立即卖出|满仓|梭哈|稳赚|保证收益|必涨|"
    r"strong buy|guaranteed (return|profit)|can't lose|cannot lose|sure thing|"
    r"buy now|sell now|all[- ]in)",
    re.IGNORECASE,
)
VERBATIM_FIELDS = {"text", "post_text", "tweet_text", "full_text", "raw_text"}
TODO_RE = re.compile(r"^\s*TODO\b", re.I)
WEAK_SOURCES = {"news", "social_lead"}            # leads, never sufficient on their own
FIRSTHAND_SOURCES = {"filing", "company_release", "earnings_call", "market_data", "industry_data"}
SERENITY_NOTICE_RE = re.compile(
    r"(不代表\s*Serenity|并非\s*Serenity|not\s+(?:the\s+)?(?:views?|opinions?|positions?)\s+of\s+Serenity|"
    r"does\s+not\s+represent\s+Serenity)", re.I)
SERENITY_NOTICE = ("框架声明：本 skill 根据 Serenity 公开发布的内容提炼研究框架，用于回测与研究分析；"
                   "报告由框架生成，不代表 Serenity 本人观点，亦非投资建议。")


def find_todos(lens: Any) -> list[str]:
    """Paths of unfilled draft fields (strings starting with TODO)."""
    return [f"lens:unfilled_todo:{path}" for path, node in _walk(lens) if isinstance(node, str) and TODO_RE.match(node)]


def _rel_close(a: float, b: float, tol: float = TOLERANCE) -> bool:
    if a == b:
        return True
    denom = max(abs(a), abs(b), 1e-12)
    return abs(a - b) / denom <= tol


def implied_market_cap(assumptions: dict[str, Any], net_debt: float = 0.0) -> float:
    revenue = float(assumptions["revenue"])
    multiple = float(assumptions["multiple"])
    basis = assumptions["multiple_basis"]
    if basis == "pe":
        margin = float(assumptions.get("net_margin", 0.0))
        return revenue * margin * multiple
    if basis == "ps":
        return revenue * multiple
    if basis == "ev_sales":
        return revenue * multiple - float(net_debt)
    raise ValueError(f"unknown multiple_basis {basis!r}")


def compute(lens: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with every derived number recomputed from inputs."""
    out = copy.deepcopy(lens)
    val = out.get("valuation", {})
    cur = val.get("current", {})
    if "price" in cur and "shares_outstanding" in cur:
        cur["market_cap"] = round(float(cur["price"]) * float(cur["shares_outstanding"]), 2)
    net_debt = float(cur.get("net_debt", 0.0))
    shares = float(cur.get("shares_outstanding", 0) or 0)
    mcap = float(cur.get("market_cap", 0) or 0)
    for sc in val.get("scenarios", []):
        a = sc.get("assumptions", {})
        try:
            imc = implied_market_cap(a, net_debt)
        except (KeyError, ValueError, TypeError):
            continue
        sc["implied_market_cap"] = round(imc, 2)
        diluted = shares * (1 + float(a.get("dilution_pct", 0.0)))
        if diluted > 0:
            sc["implied_per_share"] = round(imc / diluted, 4)
            if cur.get("price"):
                sc["vs_current_pct"] = round((sc["implied_per_share"] / float(cur["price"]) - 1) * 100, 2)
    asym = val.get("asymmetry")
    if isinstance(asym, dict) and asym.get("tam") and mcap:
        asym["mcap_to_tam"] = round(mcap / float(asym["tam"]), 4)
        if asym.get("plausible_share"):
            capt = float(asym["tam"]) * float(asym["plausible_share"])
            if capt > 0:
                asym["mcap_to_capturable_revenue"] = round(mcap / capt, 3)
    return out


def _walk(value: Any, path: str = "document"):
    yield path, value
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _walk(v, f"{path}[{i}]")


def _collect_evidence_refs(value: Any) -> list[tuple[str, str]]:
    refs = []
    for path, node in _walk(value):
        if isinstance(node, dict) and isinstance(node.get("evidence_ids"), list):
            for ref in node["evidence_ids"]:
                refs.append((path, ref))
    return refs


def _days(a: datetime, b: datetime) -> float:
    return abs((a - b).total_seconds()) / 86400


def validate(lens: dict[str, Any], schema_path: Path = SCHEMA_PATH) -> list[str]:
    todos = find_todos(lens)
    if todos:
        return todos  # a draft from `live_data.py pack`; fill judgments first
    errors = list(validate_schema_document(lens, schema_path))
    if errors:
        return errors  # structural problems first; semantic checks assume shape

    cutoff = parse_iso(lens["research_cutoff"])
    as_of = parse_iso(lens["as_of"])
    if cutoff and as_of and as_of > cutoff:
        errors.append("lens:as_of_after_research_cutoff")

    # Advice boundary: forbidden keys, forbidden phrases, verbatim post text.
    for path, node in _walk(lens):
        if isinstance(node, dict):
            for key in node:
                if key in FORBIDDEN_KEYS:
                    errors.append(f"lens:forbidden_execution_key:{path}.{key}")
                if key in VERBATIM_FIELDS:
                    errors.append(f"lens:verbatim_post_field_not_allowed:{path}.{key}")
        elif isinstance(node, str) and not path.endswith(".disclaimer") and FORBIDDEN_PHRASES.search(node):
            errors.append(f"lens:advice_language:{path}")

    # Evidence registry, links, and cutoff discipline.
    evidence = {e["evidence_id"]: e for e in lens["evidence"]}
    if len(evidence) != len(lens["evidence"]):
        errors.append("lens:duplicate_evidence_id")
    for eid, item in evidence.items():
        published = parse_iso(item.get("published_at"))
        if published is None:
            errors.append(f"lens:evidence_published_at_invalid:{eid}")
        elif cutoff and published > cutoff:
            errors.append(f"lens:evidence_after_cutoff:{eid}")
    for path, ref in _collect_evidence_refs(lens):
        if ref not in evidence:
            errors.append(f"lens:unknown_evidence_id:{ref}@{path}")

    # Market snapshot arithmetic and freshness.
    cur = lens["valuation"]["current"]
    if cur["price"] <= 0 or cur["shares_outstanding"] <= 0:
        errors.append("lens:current_price_and_shares_must_be_positive")
    else:
        computed = cur["price"] * cur["shares_outstanding"]
        if not _rel_close(computed, cur["market_cap"]):
            errors.append(f"lens:market_cap_mismatch:stated={cur['market_cap']} computed={computed:.2f}")
    if not cur["evidence_ids"]:
        errors.append("lens:current_market_data_requires_evidence")
    elif not any(evidence.get(i, {}).get("source_type") == "market_data" for i in cur["evidence_ids"]):
        errors.append("lens:current_price_requires_market_data_evidence")

    # Evidence strength: headlines and social posts are leads, not proof.
    def firsthand(ids: list[str] | None) -> bool:
        return any(evidence.get(i, {}).get("source_type") not in WEAK_SOURCES for i in ids or [] if i in evidence)

    for gname, gate in lens["gates"].items():
        if gate["status"] == "pass" and not firsthand(gate.get("evidence_ids")):
            errors.append(f"lens:gate_pass_requires_non_lead_evidence:{gname}")
    bs = lens.get("bottleneck_status")
    if isinstance(bs, dict) and bs.get("status") in {"now", "filling"} and not firsthand(bs.get("evidence_ids")):
        errors.append("lens:active_bottleneck_requires_non_lead_evidence")
    for i, lead in enumerate(lens["osint_leads"]):
        if lead["status"] == "confirmed" and not any(
                evidence.get(x, {}).get("source_type") in FIRSTHAND_SOURCES for x in lead.get("evidence_ids", [])):
            errors.append(f"lens:osint_confirmed_requires_firsthand_evidence:{i}")
    price_at = parse_iso(cur["price_as_of"])
    shares_at = parse_iso(cur["shares_as_of"])
    if price_at and cutoff and price_at > cutoff:
        errors.append("lens:price_after_cutoff")
    if price_at and as_of and _days(price_at, as_of) > MAX_PRICE_AGE_DAYS:
        errors.append("lens:stale_price")
    if shares_at and as_of and _days(shares_at, as_of) > MAX_SHARES_AGE_DAYS:
        errors.append("lens:stale_share_count")
    if cur["currency"] != lens["subject"]["currency"]:
        errors.append("lens:currency_mismatch_subject_vs_quote")

    # Scenario arithmetic, ordering, and labelling.
    scenarios = lens["valuation"]["scenarios"]
    names = [s["name"] for s in scenarios]
    if names != list(SCENARIO_ORDER):
        errors.append("lens:scenarios_must_be_bear_base_bull_in_order")
    net_debt = float(cur.get("net_debt", 0.0))
    implied = []
    for sc in scenarios:
        a = sc["assumptions"]
        if a["multiple_basis"] == "pe" and "net_margin" not in a:
            errors.append(f"lens:pe_scenario_requires_net_margin:{sc['name']}")
            continue
        try:
            imc = implied_market_cap(a, net_debt)
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(f"lens:scenario_math_error:{sc['name']}:{exc}")
            continue
        implied.append(imc)
        if not _rel_close(imc, sc["implied_market_cap"]):
            errors.append(f"lens:implied_market_cap_mismatch:{sc['name']}")
        diluted = cur["shares_outstanding"] * (1 + float(a.get("dilution_pct", 0.0)))
        if diluted > 0 and not _rel_close(imc / diluted, sc["implied_per_share"]):
            errors.append(f"lens:implied_per_share_mismatch:{sc['name']}")
        if cur["price"] > 0:
            vs = (sc["implied_per_share"] / cur["price"] - 1) * 100
            if abs(vs - sc["vs_current_pct"]) > max(0.5, abs(vs) * TOLERANCE):
                errors.append(f"lens:vs_current_pct_mismatch:{sc['name']}")
        for src in sc["assumption_sources"]:
            if src.startswith("assumption:"):
                if len(src) < len("assumption:") + 8:
                    errors.append(f"lens:assumption_source_too_vague:{sc['name']}")
            elif src not in evidence:
                errors.append(f"lens:unknown_assumption_source:{src}")
        if len(sc["narrative"].strip()) < 20:
            errors.append(f"lens:scenario_narrative_missing:{sc['name']}")
    if len(implied) == 3 and not (implied[0] <= implied[1] <= implied[2]):
        errors.append("lens:scenario_values_must_increase_bear_to_bull")
    if len(implied) == 3 and implied[0] == implied[2]:
        errors.append("lens:scenarios_have_no_spread")

    asym = lens["valuation"].get("asymmetry")
    if isinstance(asym, dict) and asym.get("tam"):
        if not asym.get("tam_source"):
            errors.append("lens:tam_requires_source")
        if "mcap_to_tam" in asym and not _rel_close(cur["market_cap"] / asym["tam"], asym["mcap_to_tam"], 0.02):
            errors.append("lens:mcap_to_tam_mismatch")

    # Red-flag veto and tier gating.
    tier = lens["research_tier"]
    vetoes = [f for f in lens["red_flags"] if f["severity"] == "veto" and f["triggered"] == "yes"]
    if vetoes and tier != "red":
        errors.append("lens:triggered_veto_requires_red_tier")
    if not lens["red_flags"]:
        errors.append("lens:red_flag_screen_missing")
    gates = lens["gates"]
    rt = lens["red_team"]
    min_len = 20
    if tier in {"green", "amber"}:
        for key in ("not_real_bottleneck", "not_monetized", "already_priced", "biggest_kill_shot"):
            if len(rt[key].strip()) < min_len:
                errors.append(f"lens:red_team_too_thin:{key}")
        if not rt["better_alternative"]["ticker"].strip() or len(rt["better_alternative"]["why"].strip()) < 10:
            errors.append("lens:red_team_requires_named_alternative")
        generic = re.compile(r"^(估值(过)?高|竞争加剧|valuation (is )?high|competition)[。.!]*$", re.I)
        if generic.match(rt["biggest_kill_shot"].strip()):
            errors.append("lens:kill_shot_is_generic")
    if tier == "green":
        if gates["real_bottleneck"]["status"] not in {"pass", "partial"}:
            errors.append("lens:green_requires_real_bottleneck_pass_or_partial")
        if any(g["status"] == "fail" for g in gates.values()):
            errors.append("lens:green_cannot_have_failed_gate")
        if len(lens["falsification"]) < 2 or not any(f["machine_checkable"] for f in lens["falsification"]):
            errors.append("lens:green_requires_two_falsifiers_one_machine_checkable")
        if len(lens["leading_signals"]) < 2:
            errors.append("lens:green_requires_two_leading_signals")
        if lens["chokepoint_of_chokepoint"]["status"] == "unknown":
            errors.append("lens:green_requires_identified_chokepoint")
    if tier == "amber" and not lens.get("rerate_triggers"):
        errors.append("lens:amber_requires_rerate_triggers")
    for f in lens["falsification"]:
        if f["machine_checkable"] and not all(k in f for k in ("metric", "operator", "threshold")):
            errors.append("lens:machine_checkable_falsifier_requires_metric_operator_threshold")
    if not lens["falsification"]:
        errors.append("lens:falsification_missing")

    # Chain map must contain the subject and at least one upstream layer.
    layers = lens["chain_map"]["layers"]
    if not any(n.get("is_subject") for layer in layers for n in layer["nodes"]):
        errors.append("lens:chain_map_missing_subject_node")
    if not any(layer["layer"].startswith("upstream") for layer in layers):
        errors.append("lens:chain_map_requires_upstream_layer")

    # Serenity memory hygiene (point-in-time, IDs only, own-words summaries).
    mem = lens["serenity_memory"]
    if mem["status"] == "available":
        if not mem.get("timeline"):
            errors.append("lens:memory_available_requires_timeline")
        for item in mem.get("timeline", []):
            d = parse_iso(item["date"] if "T" in item["date"] else item["date"] + "T00:00:00Z")
            if d is None:
                errors.append(f"lens:memory_date_invalid:{item['post_id']}")
            elif cutoff and d > cutoff:
                errors.append(f"lens:memory_event_after_cutoff:{item['post_id']}")
            if len(item.get("summary", "")) > 200:
                errors.append(f"lens:memory_summary_too_long:{item['post_id']}")
    elif mem.get("timeline"):
        errors.append("lens:memory_timeline_requires_available_status")
    known = playbook_ids()
    if known:
        for rule in lens["serenity_view"]["playbook_rules"]:
            if rule not in known:
                errors.append(f"lens:unknown_playbook_rule:{rule}")
        for f in lens["falsification"]:
            if f.get("exit_rule") and f["exit_rule"] not in known:
                errors.append(f"lens:unknown_exit_rule:{f['exit_rule']}")
        for hit in lens["archetype_hits"]:
            if hit["archetype"].startswith("ARC-") and hit["archetype"] not in known:
                errors.append(f"lens:unknown_archetype:{hit['archetype']}")
        for layer in lens["chain_map"]["layers"]:
            for node in layer["nodes"]:
                for arc in node.get("archetypes", []):
                    if arc not in known:
                        errors.append(f"lens:unknown_archetype:{arc}")
    if lens.get("schema_version") == "6.0":
        errors += validate_v6(lens, known, evidence, as_of)
    if lens["serenity_view"]["would_he_care"] == "yes" and not lens["serenity_view"]["playbook_rules"]:
        errors.append("lens:serenity_view_requires_playbook_rules")

    if len(lens["one_liner"]) > 200:
        errors.append("lens:one_liner_too_long")
    if len(lens["thirty_second_summary"]) > 700:
        errors.append("lens:thirty_second_summary_too_long")
    disclaimer = lens["disclaimer"]
    if not re.search(r"(not investment advice|非投资建议|不构成投资建议)", disclaimer, re.I):
        errors.append("lens:disclaimer_must_state_not_investment_advice")
    if not SERENITY_NOTICE_RE.search(disclaimer):
        errors.append("lens:disclaimer_must_state_not_serenity_view")
    return errors


def validate_v6(lens: dict[str, Any], known: set[str], evidence: dict[str, Any],
                as_of: datetime | None) -> list[str]:
    """Doctrine-block checks for schema_version 6.0 lenses."""
    errors: list[str] = []
    missing = [k for k in V6_REQUIRED if k not in lens]
    if missing:
        return [f"lens:v6_missing_field:{k}" for k in missing]

    live = lens["live_data"]
    retrieved = parse_iso(live["retrieved_at"])
    if retrieved is None:
        errors.append("lens:v6_live_data_retrieved_at_invalid")
    elif as_of and _days(retrieved, as_of) > MAX_PRICE_AGE_DAYS:
        errors.append("lens:v6_live_data_stale")
    for w in live.get("warnings_addressed", []):
        if len(w["handling"].strip()) < 10:
            errors.append(f"lens:v6_live_warning_not_handled:{w['warning']}")
    for eid, item in evidence.items():
        if eid.startswith("E-LIVE-") and not item.get("retrieved_at"):
            errors.append(f"lens:v6_live_evidence_requires_retrieved_at:{eid}")
    if not any(eid.startswith("E-LIVE-") for eid in evidence):
        errors.append("lens:v6_requires_live_evidence")

    fit = lens["framework_fit"]
    for rule in fit["rule_ids"]:
        if known and rule not in known:
            errors.append(f"lens:unknown_playbook_rule:{rule}")
    if not any(r.startswith("PB-FIT-") for r in fit["rule_ids"]):
        errors.append("lens:v6_framework_fit_requires_pb_fit_rule")

    vp = lens["variant_perception"]
    for code in vp["reason_codes"]:
        if not code.startswith("PB-VP-"):
            errors.append(f"lens:v6_reason_code_must_be_pb_vp:{code}")
        elif known and code not in known:
            errors.append(f"lens:unknown_playbook_rule:{code}")
    if not re.search(r"\d", vp["our_view"]):
        errors.append("lens:v6_our_view_requires_numbers")
    if vp["our_view"].strip() == vp["consensus"].strip():
        errors.append("lens:v6_our_view_equals_consensus")
    for src in vp["consensus_sources"]:
        if src.startswith("assumption:"):
            if len(src) < len("assumption:") + 8:
                errors.append("lens:v6_consensus_source_too_vague")
        elif src not in evidence:
            errors.append(f"lens:unknown_evidence_id:{src}@variant_perception.consensus_sources")
    fn = vp["first_number_to_prove_wrong"]
    if parse_iso(fn["check_by"] if "T" in fn["check_by"] else fn["check_by"] + "T00:00:00Z") is None:
        errors.append("lens:v6_first_number_check_by_invalid")

    picks = lens["next_hop_picks"]
    subject = lens["subject"]["resolved_symbol"].upper()
    for p in picks:
        if p["ticker"].upper() == subject:
            errors.append("lens:v6_next_hop_cannot_be_subject")
        for arc in p.get("archetypes", []):
            if known and arc not in known:
                errors.append(f"lens:unknown_archetype:{arc}")

    tier = lens["research_tier"]
    status = lens["bottleneck_status"]["status"]
    stage = lens["phase"]["stage"]
    if tier == "green":
        if status in {"not_bottleneck", "unknown", "resolving"}:
            errors.append("lens:v6_green_requires_live_bottleneck_status")
        if stage in {"rnd", "decline"}:
            errors.append("lens:v6_green_incompatible_with_phase")
        if fit["role"] == "diluter_or_story":
            errors.append("lens:v6_green_incompatible_with_diluter_role")
    if fit["fit"] in {"weak", "not_applicable"} and status == "now":
        errors.append("lens:v6_weak_fit_cannot_claim_active_bottleneck")
    return errors


def finish(path: Path, lens: dict[str, Any], out_dir: Path | None = None, stem: str | None = None) -> int:
    from render_report import to_html, to_markdown  # noqa: WPS433 (local import keeps validate dependency-light)
    from verify_report import verify, verify_markdown

    todos = find_todos(lens)
    if todos:
        for t in todos:
            print(f"TODO: {t.split(':', 2)[-1]}")
        print(f"Refusing to finish: {len(todos)} draft field(s) still start with TODO.")
        return 1
    out = compute(lens)
    errors = validate(out)
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_dir = out_dir or path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = stem or path.stem.replace("-lens", "-report").replace("lens-draft", "report")
    md, htm = out_dir / f"{stem}.md", out_dir / f"{stem}.html"
    md.write_text(to_markdown(out), encoding="utf-8")
    htm.write_text(to_html(out), encoding="utf-8")
    problems = verify_markdown(md.read_text(encoding="utf-8"), path) + verify(htm.read_text(encoding="utf-8"))
    if problems:
        for e in problems:
            print(f"ERROR: {e}")
        return 1
    print(f"OK: {out['lens_id']} computed, validated, rendered and verified -> {md} , {htm}")
    return 0


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path}: top-level object required")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compute", help="recompute derived numbers and write the lens")
    c.add_argument("path", type=Path)
    c.add_argument("--out", type=Path, help="output path (default: overwrite input)")
    v = sub.add_parser("validate", help="validate a SerenityLens JSON")
    v.add_argument("path", type=Path)
    f = sub.add_parser("finish", help="TODO check -> compute -> validate -> render -> verify, in one step")
    f.add_argument("path", type=Path)
    f.add_argument("--out-dir", type=Path, help="render directory (default: next to the lens)")
    f.add_argument("--stem", help="report file stem (default: lens file stem)")
    args = parser.parse_args(argv)
    lens = _load(args.path)
    if args.cmd == "finish":
        return finish(args.path, lens, args.out_dir, args.stem)
    if args.cmd == "compute":
        out = compute(lens)
        target = args.out or args.path
        target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK: derived numbers written to {target}")
        return 0
    errors = validate(lens)
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1
    print(f"OK: SerenityLens {lens['lens_id']} passed v{lens.get('schema_version', '5.0')} contract checks (structure, arithmetic, cutoff, gating, advice boundary).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
