#!/usr/bin/env python3
"""ETF audit: where the chokepoint atlas and the theme ETFs disagree.

Index funds own what is already large and liquid. A chokepoint that no theme
ETF holds is, by construction, not yet consensus; a heavy ETF holding that the
atlas never mentions is either a deliberate exclusion (integrator, diluted
exposure) or a mapping gap. This tool lists both, offline.

Inputs: assets/etf-holdings/<ETF>.json (refresh with
`python connectors/live_data.py etf-holdings SMH --out assets/etf-holdings/SMH.json`),
assets/chokepoint-atlas.json, and assets/ticker-truth.json for official names.

  python scripts/etf_audit.py                       # all ETFs in assets/etf-holdings
  python scripts/etf_audit.py --md work/etf-audit.md --json work/etf-audit.json

Matching is by normalized company name (official names from ticker-truth plus
the atlas name), so it is a lead list: confirm before acting. N-PORT holdings
are quarter-end snapshots filed ~60 days later.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ticker_truth as TT  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HOLDINGS_DIR = ROOT / "assets" / "etf-holdings"
MATCH = 0.8


def atlas_holders(atlas: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for chain in atlas["chains"]:
        for node in chain["nodes"]:
            for h in node.get("holders", []):
                t = h["ticker"].upper()
                rec = out.setdefault(t, {"ticker": t, "name": h.get("name"), "positions": [], "basis": set()})
                rec["positions"].append({"chain": chain["chain_id"], "node": node["node_id"], "status": node["status"]})
                rec["basis"].add(h.get("basis"))
    return out


def audit(etfs: list[dict[str, Any]], atlas: dict[str, Any], truth: dict[str, Any]) -> dict[str, Any]:
    holders = atlas_holders(atlas)
    entries = truth.get("entries", {})
    names = {t: [h["name"]] + (entries.get(t) or {}).get("names", []) for t, h in holders.items()}
    covered: dict[str, list[dict[str, Any]]] = {t: [] for t in holders}
    gaps: dict[str, dict[str, Any]] = {}
    for etf in etfs:
        for h in etf["holdings"]:
            best_t, best = None, 0.0
            for t, ns in names.items():
                sc = max((TT.similarity(h["name"], n) for n in ns if n), default=0.0)
                if sc > best:
                    best_t, best = t, sc
            if best_t and best >= MATCH:
                covered[best_t].append({"etf": etf["etf"], "pct": h.get("pct"), "period_end": etf.get("period_end")})
            else:
                g = gaps.setdefault(TT.norm_name(h["name"]), {"name": h["name"], "isin": h.get("isin"), "country": h.get("country"), "etfs": []})
                g["etfs"].append({"etf": etf["etf"], "pct": h.get("pct")})
    in_etf, outside = [], []
    for t, rec in sorted(holders.items()):
        row = {"ticker": t, "name": rec["name"], "statuses": sorted({p["status"] for p in rec["positions"]}),
               "chains": sorted({p["chain"] for p in rec["positions"]}), "serenity_lead": "serenity_lead" in rec["basis"]}
        if covered[t]:
            in_etf.append({**row, "etfs": covered[t], "max_pct": max((c["pct"] or 0) for c in covered[t])})
        else:
            outside.append(row)
    live = {"now", "filling", "coming"}
    early = [r for r in outside if set(r["statuses"]) & live]
    gap_rows = sorted(gaps.values(), key=lambda g: -max((e["pct"] or 0) for e in g["etfs"]))
    for g in gap_rows:
        g["max_pct"] = max((e["pct"] or 0) for e in g["etfs"])
    return {"etfs": [{"etf": e["etf"], "fund": e.get("fund"), "period_end": e.get("period_end"), "filed": e.get("filed"),
                      "holdings": len(e["holdings"]), "source_url": e.get("source_url")} for e in etfs],
            "atlas_holders": len(holders), "in_etf": sorted(in_etf, key=lambda r: -r["max_pct"]),
            "outside_etf_live_chokepoints": early, "outside_etf_other": [r for r in outside if r not in early],
            "etf_heavy_not_in_atlas": gap_rows,
            "note": "Name matching on quarter-end N-PORT data: leads to verify, not conclusions or advice."}


def to_markdown(res: dict[str, Any], top_gaps: int = 15) -> str:
    L = ["# ETF 覆盖审计（图谱 vs 主题 ETF）", ""]
    L.append("数据：" + "；".join(f"{e['etf']}（{e['fund']}，持仓截至 {e['period_end']}，申报 {e['filed']}，{e['holdings']} 只）" for e in res["etfs"]))
    n_in, n_out = len(res["in_etf"]), len(res["outside_etf_live_chokepoints"]) + len(res["outside_etf_other"])
    L += ["", f"图谱持有者 {res['atlas_holders']} 个：被至少一只 ETF 持有 {n_in} 个，不在任何 ETF 中 {n_out} 个。", "",
          "## 1. 不在任何主题 ETF 里的“正在卡/正在订满/即将卡”标的（非共识线索）", "",
          "| 代码 | 名称 | 状态 | 链 | Serenity 线索 |", "|---|---|---|---|---|"]
    for r in res["outside_etf_live_chokepoints"]:
        L.append(f"| `{r['ticker']}` | {r['name']} | {', '.join(r['statuses'])} | {', '.join(r['chains'])} | {'是' if r['serenity_lead'] else '—'} |")
    L += ["", "## 2. 已被 ETF 持有的图谱标的（已进入指数资金视野）", "", "| 代码 | 名称 | 最高权重 | ETF |", "|---|---|---:|---|"]
    for r in res["in_etf"]:
        L.append(f"| `{r['ticker']}` | {r['name']} | {r['max_pct']:.2f}% | {', '.join(sorted({c['etf'] for c in r['etfs']}))} |")
    L += ["", f"## 3. ETF 重仓但图谱未收录（前 {top_gaps}；可能是有意排除的整合商，也可能是图谱缺口）", "",
          "| 持仓 | 国家 | 最高权重 | ETF |", "|---|---|---:|---|"]
    for g in res["etf_heavy_not_in_atlas"][:top_gaps]:
        L.append(f"| {g['name']} | {g.get('country') or '—'} | {g['max_pct']:.2f}% | {', '.join(sorted({e['etf'] for e in g['etfs']}))} |")
    L += ["", "> " + res["note"], ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--holdings", type=Path, nargs="*", help="holdings JSON files (default: assets/etf-holdings/*.json)")
    ap.add_argument("--atlas", type=Path, default=TT.ATLAS_PATH)
    ap.add_argument("--truth", type=Path, default=TT.TRUTH_PATH)
    ap.add_argument("--md", type=Path); ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    files = args.holdings or sorted(HOLDINGS_DIR.glob("*.json"))
    if not files:
        print("ERROR: no ETF holdings files; run `python connectors/live_data.py etf-holdings SMH --out assets/etf-holdings/SMH.json`")
        return 1
    etfs = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    res = audit(etfs, json.loads(args.atlas.read_text(encoding="utf-8")), TT.load(args.truth))
    md = to_markdown(res)
    if args.json:
        args.json.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md:
        args.md.write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
