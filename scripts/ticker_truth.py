#!/usr/bin/env python3
"""Ticker truth table: catch wrong tickers, names and currencies before they reach a report.

A research report that pins the right story on the wrong ticker is worse than
no report. This tool keeps assets/ticker-truth.json, a dated table of official
identities for every atlas holder, example and tracked symbol, built from
live snapshots (quote provider name + currency + exchange, SEC registrant
name for US listings, exchange-side short name for A/H shares).

  build  --snapshots DIR     Offline: fold connector snapshots
                             (live_data.py batch ... --out-dir DIR) into the table.
  check                      Offline: atlas holder names, example lenses and
                             tracking ledgers against the table. Exit 1 on errors.
  lookup <TICKER>            Print one entry.

Network-free; refresh the snapshots with the connector, then rebuild.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRUTH_PATH = ROOT / "assets" / "ticker-truth.json"
ATLAS_PATH = ROOT / "assets" / "chokepoint-atlas.json"
STOP = {"inc", "corp", "corporation", "co", "company", "ltd", "limited", "plc", "sa", "s", "a", "se", "ag", "nv", "n", "v",
        "ab", "publ", "holdings", "holding", "group", "the", "technologies", "technology", "industries", "industrial",
        "international", "co.,", "cayman", "class", "ordinary", "shares", "adr", "de", "and", "&"}
NAME_MIN_SIMILARITY = 0.55


def norm_name(name: str | None) -> str:
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af ]+", " ", (name or "").lower())
    return " ".join(t for t in text.split() if t not in STOP)


def _initials(name: str) -> str:
    words = re.sub(r"[^A-Za-z ]+", " ", name).split()
    return "".join(w[0] for w in words if w.lower() not in {"limited", "ltd", "inc", "plc", "the", "of", "and"}).lower()


def _composed(compact: str, tokens: list[str]) -> bool:
    """'leaderdrive' is composed of tokens of 'leader harmonious drive systems' (in order)."""
    if not compact:
        return False
    i = 0
    for t in tokens:
        if compact.startswith(t, i):
            i += len(t)
            if i == len(compact):
                return True
    return False


def similarity(a: str | None, b: str | None) -> float:
    na, nb = norm_name(a), norm_name(b)
    if not na or not nb:
        return 0.0
    ta, tb = na.split(), nb.split()
    if set(ta) <= set(tb) or set(tb) <= set(ta):
        return 1.0
    for short, long_raw, long_norm in ((a or "", b or "", nb), (b or "", a or "", na)):
        s = re.sub(r"[^A-Za-z]", "", short)
        if 2 <= len(s) <= 6 and s.isupper() and s.lower() == _initials(long_raw):
            return 1.0
        short_norm = norm_name(short)
        if " " not in short_norm and _composed(short_norm, long_norm.split()):
            return 1.0
    # the first distinctive word carries the identity ("WIN" vs "NXP" Semiconductors)
    head = difflib.SequenceMatcher(None, ta[0], tb[0]).ratio()
    sa, sb = set(ta), set(tb)
    jacc = len(sa & sb) / max(1, min(len(sa), len(sb)))
    full = difflib.SequenceMatcher(None, na, nb).ratio()
    return round(max(jacc, full) * (1.0 if head >= 0.8 else 0.5), 3)


def best_similarity(name: str, entry: dict[str, Any]) -> float:
    return max((similarity(name, n) for n in entry.get("names", [])), default=0.0)


def load(path: Path = TRUTH_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"entries": {}}


def entry_from_snapshot(snap: dict[str, Any]) -> dict[str, Any] | None:
    q = snap.get("quote") or {}
    if q.get("status") != "ok":
        return None
    subj = snap.get("subject") or {}
    names = [q.get("name")]
    sec = snap.get("sec_identity") or {}
    if sec.get("status") == "ok":
        names.append(sec.get("name"))
    xch = snap.get("exchange") or {}
    q2 = xch.get("second_quote") or {}
    if q2.get("status") == "ok":
        names.append(q2.get("name"))
    disc = xch.get("disclosures") or {}
    if disc.get("issuer"):
        names.append(disc["issuer"])
    mrev = xch.get("monthly_revenue") or {}
    if mrev.get("company"):
        names.append(mrev["company"])
    names = [n for i, n in enumerate(names) if n and n not in names[:i]]
    sources = [q.get("source_url")] + ([sec.get("source_url")] if sec.get("status") == "ok" else []) \
        + ([q2.get("source_url")] if q2.get("status") == "ok" else [])
    return {"symbol": subj.get("symbol") or q.get("symbol"), "official_name": names[0], "names": names,
            "currency": q.get("currency"), "exchange": q.get("exchange"),
            "venue": "US" if subj.get("us_listed") else (subj.get("exchange") or "?"),
            "sec_cik": sec.get("cik") if sec.get("status") == "ok" else None,
            "verified_at": snap.get("retrieved_at"), "sources": [s for s in sources if s]}


def build(snap_dir: Path, out: Path = TRUTH_PATH) -> dict[str, Any]:
    truth = load(out)
    entries = truth.get("entries", {})
    added = 0
    for p in sorted(snap_dir.glob("*.json")):
        try:
            snap = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if snap.get("kind") != "live_snapshot":
            continue
        e = entry_from_snapshot(snap)
        if e and e["symbol"]:
            entries[e["symbol"].upper()] = e
            added += 1
    truth = {"truth_version": "1", "as_of": datetime.now(timezone.utc).date().isoformat(),
             "description": "Official identities (name, currency, exchange) per symbol from dated live snapshots. "
                            "A guard against wrong-ticker reports, not investment data.",
             "entries": dict(sorted(entries.items()))}
    out.write_text(json.dumps(truth, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"written": str(out), "updated": added, "total": len(entries)}


def check(truth: dict[str, Any], atlas_path: Path = ATLAS_PATH, lens_paths: list[Path] | None = None,
          ledgers: list[Path] | None = None) -> dict[str, Any]:
    entries = truth.get("entries", {})
    errors: list[str] = []
    warnings: list[str] = []
    atlas = json.loads(atlas_path.read_text(encoding="utf-8")) if atlas_path.is_file() else {"chains": []}
    seen = set()
    for chain in atlas["chains"]:
        for node in chain["nodes"]:
            for h in node.get("holders", []):
                t = h["ticker"].upper()
                if t in seen:
                    continue
                seen.add(t)
                e = entries.get(t)
                if not e:
                    warnings.append(f"atlas {t}: not in ticker-truth (rebuild after adding atlas holders)")
                    continue
                sim = best_similarity(h.get("name", ""), e)
                if sim < NAME_MIN_SIMILARITY:
                    errors.append(f"atlas {t}: name '{h.get('name')}' does not match official '{e['official_name']}' (similarity {sim})")
    for p in lens_paths or []:
        lens = json.loads(p.read_text(encoding="utf-8"))
        subj = lens.get("subject") or {}
        t = (subj.get("resolved_symbol") or subj.get("ticker") or "").upper()
        e = entries.get(t)
        if not e:
            warnings.append(f"{p.name}: {t} not in ticker-truth")
            continue
        sim = best_similarity(subj.get("company_name", ""), e)
        if sim < NAME_MIN_SIMILARITY:
            errors.append(f"{p.name}: company_name '{subj.get('company_name')}' vs official '{e['official_name']}' (similarity {sim})")
        if subj.get("currency") and e.get("currency") and subj["currency"].upper() != e["currency"].upper():
            errors.append(f"{p.name}: currency {subj['currency']} but {t} trades in {e['currency']}")
    for p in ledgers or []:
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            t = (row.get("symbol") or "").upper()
            e = entries.get(t)
            if not e:
                warnings.append(f"{p.name}: {t} not in ticker-truth")
            elif row.get("currency") and e.get("currency") and row["currency"].upper() != e["currency"].upper():
                errors.append(f"{p.name}: {row.get('lens_id')} currency {row['currency']} but {t} trades in {e['currency']}")
    return {"ok": not errors, "entries": len(entries), "as_of": truth.get("as_of"), "errors": errors, "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--truth", type=Path, default=TRUTH_PATH)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--snapshots", type=Path, required=True)
    c = sub.add_parser("check"); c.add_argument("--lens", type=Path, action="append")
    c.add_argument("--ledger", type=Path, action="append"); c.add_argument("--atlas", type=Path, default=ATLAS_PATH)
    lk = sub.add_parser("lookup"); lk.add_argument("ticker")
    args = ap.parse_args(argv)
    if args.cmd == "build":
        print(json.dumps(build(args.snapshots, args.truth), ensure_ascii=False))
        return 0
    truth = load(args.truth)
    if args.cmd == "lookup":
        e = truth.get("entries", {}).get(args.ticker.upper())
        print(json.dumps(e or {"error": f"{args.ticker} not in ticker-truth"}, ensure_ascii=False, indent=2))
        return 0 if e else 1
    lenses = args.lens if args.lens is not None else sorted((ROOT / "examples").glob("*-serenity-lens.json"))
    ledgers = args.ledger if args.ledger is not None else sorted((ROOT / "tracking").glob("*.jsonl"))
    res = check(truth, args.atlas, lenses, ledgers)
    print(f"{'OK' if res['ok'] else 'FAIL'}: ticker-truth {res['entries']} entries (as of {res['as_of']})")
    for e in res["errors"]:
        print("  ERROR " + e)
    for w in res["warnings"]:
        print("  warn  " + w)
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
