#!/usr/bin/env python3
"""Doctrine lead sheet: live snapshot(s) + chokepoint atlas -> first-pass leads.

Network-free.  Reads JSON written by `connectors/live_data.py snapshot` and
`assets/chokepoint-atlas.json`, then applies mechanical doctrine screens:

  * pricing power      gross-margin change y/y            (PB-SIG-04)
  * acceleration       revenue y/y and q/q                (PB-PHASE-04, PB-LAW-08)
  * dilution radar     share-count change, shelf/ATM, 8-K 3.02 (PB-FIN-01/02/03/11)
  * runway             cash vs average FCF burn           (PB-FIN-06, PB-PHASE-01)
  * concentration      SEC full-text hits                 (PB-RISK-01, ARC-SOLE-SOURCE)
  * capacity language  SEC full-text hits                 (PB-CAP-04)
  * discovery          new 13G/13D, insider filings       (PB-SIG-09, PB-SIG-10)
  * atlas              node, status, next-hop candidates  (PB-HUNT-08)

Outputs are GUESSES for the analyst to confirm (framework_fit, phase), not
conclusions, ratings, or trade instructions.

  python3 scripts/chokepoint_scan.py snapshot1.json [snapshot2.json ...] [--md out.md] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas import ATLAS_PATH, load_atlas, lookup_ticker  # noqa: E402


def _last(series: list[dict[str, Any]] | None, key: str = "pct") -> float | None:
    if not series:
        return None
    v = series[-1].get(key)
    return float(v) if isinstance(v, (int, float)) else None


PRIMARY_FORMS = {"10-K", "10-Q", "20-F", "40-F", "10-K/A", "10-Q/A", "20-F/A", "8-K", "6-K", "S-1", "S-3", "F-1", "F-3", "424B5"}
EXHIBIT_NAME = re.compile(r"(?i)(^|/)(ex[-_]?\d|exhibit|dex\d)")


def _is_primary_report(hit: dict[str, Any]) -> bool:
    """True when an SEC full-text hit is the filing's own document, not an exhibit.

    Going-concern language inside a merger target's financials, a lender's
    exhibit, or an auditor consent is not the registrant's own warning.
    """
    if "primary_document" in hit:
        return bool(hit["primary_document"])
    ftype = (hit.get("file_type") or "").upper()
    if ftype:
        return ftype in PRIMARY_FORMS
    name = (hit.get("url") or "").rsplit("/", 1)[-1]
    return bool(name) and not EXHIBIT_NAME.search(name)


def scan_snapshot(snap: dict[str, Any], atlas: dict[str, Any]) -> dict[str, Any]:
    subject = snap.get("subject", {})
    symbol = subject.get("symbol") or snap.get("quote", {}).get("symbol") or "?"
    quote = snap.get("quote", {}) or {}
    fund = (snap.get("fundamentals") or {}).get("summary") or {}
    filings = snap.get("filings") or {}
    fts = snap.get("fts") if isinstance(snap.get("fts"), dict) else {}
    signals: list[dict[str, Any]] = []

    def add(kind: str, direction: str, detail: str, rule: str) -> None:
        signals.append({"signal": kind, "direction": direction, "detail": detail, "rule": rule})

    gm_pp = fund.get("gross_margin_change_yoy_pp")
    gm_last = _last(fund.get("gross_margin_quarterly"))
    if isinstance(gm_pp, (int, float)):
        if gm_pp >= 5:
            add("pricing_power", "positive", f"gross margin +{gm_pp:.1f}pp y/y (latest {gm_last}%)", "PB-SIG-04")
        elif gm_pp <= -5:
            add("pricing_power", "negative", f"gross margin {gm_pp:.1f}pp y/y", "PB-SIG-04")
    if gm_last is not None and gm_last < 0:
        add("gross_margin_negative", "negative", f"latest quarterly gross margin {gm_last}% — check one-offs before concluding", "PB-DATA-03")

    yoy = fund.get("revenue_yoy_pct")
    qoq = fund.get("revenue_qoq_pct")
    if isinstance(yoy, (int, float)):
        if yoy >= 50:
            add("acceleration", "positive", f"revenue +{yoy:.0f}% y/y" + (f", {qoq:+.0f}% q/q" if isinstance(qoq, (int, float)) else ""), "PB-PHASE-04")
        elif yoy <= -10:
            add("acceleration", "negative", f"revenue {yoy:.0f}% y/y", "PB-PHASE-06")

    sc = fund.get("share_count_change_pct_vs_4_obs_ago")
    if isinstance(sc, (int, float)) and sc >= 10:
        add("dilution", "negative", f"share count +{sc:.0f}% vs four observations ago — think in market cap", "PB-FIN-11")
    for f in filings.get("flags", []) or []:
        direction = "positive" if f.get("flag", "").startswith(("new_13", "insider_buy")) else "check"
        detail = f.get("check", "")
        if "likely_underwritten" in f:
            detail = f"{f.get('likely_underwritten')}/{f.get('count')} look underwritten (8-K 1.01 within 2 days). " + detail
        add(f.get("flag", "filing_flag"), direction, detail, f.get("doctrine", "PB-FIN-01"))

    disc = (snap.get("exchange") or {}).get("disclosures") or {}
    for f in disc.get("flags", []) or []:
        if f.get("flag") == "periodic_report":
            continue
        latest = (f.get("latest") or {}).get("title", "")
        add(f"exchange_{f['flag']}", f.get("direction", "check"),
            f"{disc.get('system')}: {f.get('count')} title hit(s), latest {(f.get('latest') or {}).get('published_at', '')[:10]} «{latest[:80]}» — open the document",
            f.get("doctrine", "PB-DATA-01"))
    mrev = (snap.get("exchange") or {}).get("monthly_revenue") or {}
    if mrev.get("status") == "ok" and isinstance(mrev.get("yoy_pct"), (int, float)):
        y = mrev["yoy_pct"]
        if y >= 50:
            add("monthly_revenue_acceleration", "positive", f"{mrev['month']} revenue +{y:.0f}% y/y (YTD {mrev.get('ytd_yoy_pct')}%)", "PB-PHASE-04")
        elif y <= -10:
            add("monthly_revenue_acceleration", "negative", f"{mrev['month']} revenue {y:.0f}% y/y", "PB-PHASE-06")

    runway = fund.get("runway_quarters_at_avg_fcf_burn")
    if isinstance(runway, (int, float)) and runway < 6:
        add("runway", "negative", f"~{runway:.1f} quarters of runway at average FCF burn — financing likely", "PB-FIN-06")

    def fts_total(key: str) -> int:
        block = fts.get(key) if isinstance(fts, dict) else None
        return int(block.get("total") or 0) if isinstance(block, dict) else 0

    if fts_total("going_concern"):
        hits = (fts.get("going_concern") or {}).get("hits") or []
        primary = [h for h in hits if _is_primary_report(h)]
        if primary or not hits:
            add("going_concern", "negative", f"going-concern / substantial-doubt language in {len(primary) or 'unknown'} primary filing document(s) — read the context (risk factor vs auditor opinion)", "PB-PHASE-01")
        else:
            add("going_concern_exhibit_only", "check", f"{len(hits)} going-concern hits are exhibits only (acquired-company or counterparty financials?) — not the registrant's own warning until read", "PB-PHASE-01")
    if fts_total("customer_concentration"):
        add("customer_concentration", "check", f"{fts_total('customer_concentration')} filings mention major-customer concentration", "PB-RISK-01")
    if fts_total("supply_concentration"):
        add("supply_concentration", "check", "sole/single-source language: is the company the sole source, or dependent on one?", "ARC-SOLE-SOURCE")
    if fts_total("capacity_signal"):
        add("capacity_language", "check", "capacity/lead-time language in filings — demand-limited or capacity-limited?", "PB-CAP-04")
    if fts_total("atm_program"):
        add("atm_language", "check", "at-the-market / equity distribution language — size the overhang", "PB-FIN-02")

    dd = quote.get("drawdown_from_52w_high_pct")
    if isinstance(dd, (int, float)) and dd <= -50:
        add("drawdown", "check", f"{dd:.0f}% from 52-week high — macro correction or thesis break?", "PB-TIME-06")

    at = lookup_ticker(atlas, symbol)
    positions = at["positions"]
    statuses = {p["status"] for p in positions}
    neg = {s["signal"] for s in signals if s["direction"] == "negative"}
    ttm = fund.get("revenue_ttm")
    tiny_revenue = isinstance(ttm, (int, float)) and ttm < 10_000_000
    if "going_concern" in neg or ("dilution" in neg and tiny_revenue):
        fit_guess = {"role": "diluter_or_story", "fit": "weak", "rule": "PB-FIT-05"}
    elif statuses & {"now", "filling", "coming", "monopoly_not_bottleneck"}:
        fit_guess = {"role": "chokepoint", "fit": "strong" if statuses & {"now", "filling"} else "partial", "rule": "PB-FIT-01"}
    elif positions:
        fit_guess = {"role": "integrator_or_commodity", "fit": "partial", "rule": "PB-FIT-04"}
    else:
        fit_guess = {"role": "unknown", "fit": "unknown", "rule": "PB-HUNT-08",
                     "note": "not in atlas — map who it buys from / sells to before judging"}

    if tiny_revenue:
        phase_guess = "rnd_or_sampling"
    elif isinstance(yoy, (int, float)) and yoy >= 50:
        phase_guess = "volume_ramp"
    elif isinstance(yoy, (int, float)) and yoy <= -20:
        phase_guess = "decline_or_cyclical_trough"
    else:
        phase_guess = "steady_state_or_qualification"

    next_hop: list[dict[str, Any]] = []
    for p in positions:
        for c in p["next_hop_candidates"][:5]:
            if all(c["ticker"] != x["ticker"] for x in next_hop):
                next_hop.append({k: c[k] for k in ("ticker", "name", "node", "status", "basis")})

    questions = [
        "Who are the top customers and what share of capacity does the company hold? (PB-LAW-03)",
        "Can the largest customer build this in-house within 3 years? (PB-LAW-02)",
        "What does the latest call say about allocation, lead times, or capacity? (PB-HUNT-11)",
    ]
    if any(s["signal"] in {"dilution", "atm_language", "shelf_registration_on_file"} for s in signals):
        questions.append("How large is the shelf/ATM versus market cap, and who bought any placement? (PB-FIN-01, PB-FIN-03)")
    if not positions:
        questions.append("Which atlas chain does it belong to? Add a node if it is a genuine chokepoint.")

    return {
        "symbol": symbol,
        "retrieved_at": snap.get("retrieved_at"),
        "price": quote.get("price"), "currency": quote.get("currency"),
        "market_cap_calc": (snap.get("market_current") or {}).get("market_cap"),
        "drawdown_from_52w_high_pct": dd,
        "revenue_ttm": ttm, "revenue_yoy_pct": yoy,
        "atlas": [{"chain": p["chain_id"], "node": p["node_id"], "status": p["status"], "peers": p["peers"]} for p in positions],
        "signals": signals,
        "framework_fit_guess": fit_guess,
        "phase_guess": phase_guess,
        "next_hop_candidates": next_hop,
        "questions": questions,
        "snapshot_warnings": snap.get("warnings", []),
        "note": "Mechanical first pass; confirm every guess with primary sources before writing a lens.",
    }


def to_markdown(rows: list[dict[str, Any]]) -> str:
    out = ["# 卡点线索表（chokepoint_scan）", "", "> 机械初筛，所有判断都是待确认的猜测；不构成投资建议。", "",
           "| 代码 | 市值(计算) | 52周回撤 | 营收同比 | 适配猜测 | 阶段猜测 | 图谱位置 | 主要信号 | 下一跳 |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        mc = r["market_cap_calc"]
        mc_s = f"{mc / 1e9:.2f}B {r['currency']}" if isinstance(mc, (int, float)) else "—"
        sig = "；".join(f"{s['signal']}({s['direction'][0]})" for s in r["signals"][:6]) or "—"
        at = "；".join(f"{a['node']}:{a['status']}" for a in r["atlas"]) or "未收录"
        nh = ", ".join(x["ticker"] for x in r["next_hop_candidates"][:4]) or "—"
        dd = f"{r['drawdown_from_52w_high_pct']:.0f}%" if isinstance(r["drawdown_from_52w_high_pct"], (int, float)) else "—"
        yoy = f"{r['revenue_yoy_pct']:+.0f}%" if isinstance(r["revenue_yoy_pct"], (int, float)) else "—"
        fit = r["framework_fit_guess"]
        out.append(f"| `{r['symbol']}` | {mc_s} | {dd} | {yoy} | {fit['role']}/{fit['fit']} | {r['phase_guess']} | {at} | {sig} | {nh} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snapshots", nargs="+", type=Path)
    ap.add_argument("--atlas", type=Path, default=ATLAS_PATH)
    ap.add_argument("--json", type=Path, help="write full lead sheet JSON here")
    ap.add_argument("--md", type=Path, help="write markdown lead table here")
    args = ap.parse_args(argv)
    atlas = load_atlas(args.atlas)
    rows = [scan_snapshot(json.loads(p.read_text(encoding="utf-8")), atlas) for p in args.snapshots]
    if args.json:
        args.json.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md:
        args.md.write_text(to_markdown(rows), encoding="utf-8")
    if not args.json and not args.md:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(to_markdown(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())