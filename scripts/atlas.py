#!/usr/bin/env python3
"""Chokepoint atlas: offline lookup over assets/chokepoint-atlas.json.

Network-free and dependency-free.  Subcommands:

  validate          Check structure: unique node IDs, upstream references,
                    no cycles, known taxonomy codes, statuses, archetypes,
                    basis values, post IDs.
  ticker <T>        Where a ticker sits: chain, node, status, upstream path,
                    same-node peers, and next-hop candidates (holders of the
                    upstream nodes, i.e. "go a few levels deeper").
  theme <keyword>   Nodes whose chain/node name or holder matches a keyword.
  path <node_id>    Full upstream tree of a node.
  render            Write references/chokepoint-atlas.md from the JSON.

The atlas records research leads as of its `as_of` date; it is not live data
and not investment advice.  Always confirm with connectors/live_data.py.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ATLAS_PATH = ROOT / "assets" / "chokepoint-atlas.json"
TAXONOMY_PATH = ROOT / "references" / "supply-chain-taxonomy.md"
MD_PATH = ROOT / "references" / "chokepoint-atlas.md"
STATUSES = {"now", "filling", "coming", "monopoly_not_bottleneck", "diluted_exposure", "resolving", "not_bottleneck", "unknown"}
KINDS = {"material", "demand", "none"}
BASES = {"serenity_lead", "author_lead", "industry_knowledge", "inferred"}  # author_lead = legacy alias
STATUS_RANK = {"now": 0, "filling": 1, "coming": 2, "monopoly_not_bottleneck": 3, "diluted_exposure": 4,
               "resolving": 5, "unknown": 6, "not_bottleneck": 7}

sys.path.insert(0, str(Path(__file__).resolve().parent))


def load_atlas(path: Path = ATLAS_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def taxonomy_codes(path: Path = TAXONOMY_PATH) -> set[str]:
    if not path.exists():
        return set()
    return set(re.findall(r"^\| (L[0-4](?:\.[A-Z]+)+) \|", path.read_text(encoding="utf-8"), re.M)) | {"OTHER"}


def index(atlas: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    for chain in atlas["chains"]:
        for node in chain["nodes"]:
            nodes[node["node_id"]] = {**node, "chain_id": chain["chain_id"], "chain_name": chain["name"]}
    return nodes


def norm(t: str) -> str:
    return t.strip().upper().lstrip("$")


def validate(atlas: dict[str, Any]) -> list[str]:
    from serenity_lens import playbook_ids

    errors: list[str] = []
    known = playbook_ids()
    codes = taxonomy_codes()
    seen: set[str] = set()
    for key in ("atlas_version", "as_of", "chains", "disclaimer"):
        if key not in atlas:
            errors.append(f"atlas:missing:{key}")
    for chain in atlas.get("chains", []):
        for node in chain.get("nodes", []):
            nid = node.get("node_id", "?")
            if nid in seen:
                errors.append(f"atlas:duplicate_node:{nid}")
            seen.add(nid)
            if node.get("status") not in STATUSES:
                errors.append(f"atlas:bad_status:{nid}")
            if node.get("kind") not in KINDS:
                errors.append(f"atlas:bad_kind:{nid}")
            if codes and node.get("taxonomy") not in codes:
                errors.append(f"atlas:unknown_taxonomy:{nid}:{node.get('taxonomy')}")
            for arc in node.get("archetypes", []):
                if known and arc not in known:
                    errors.append(f"atlas:unknown_archetype:{nid}:{arc}")
            if not node.get("holders"):
                errors.append(f"atlas:node_without_holders:{nid}")
            for h in node.get("holders", []):
                if h.get("basis") not in BASES:
                    errors.append(f"atlas:bad_basis:{nid}:{h.get('ticker')}")
                if h.get("basis") in {"serenity_lead", "author_lead"} and not h.get("post_ids"):
                    errors.append(f"atlas:serenity_lead_requires_post_ids:{nid}:{h.get('ticker')}")
                for pid in h.get("post_ids", []):
                    if not re.fullmatch(r"\d{15,20}", str(pid)):
                        errors.append(f"atlas:bad_post_id:{nid}:{pid}")
    nodes = index(atlas)
    for nid, node in nodes.items():
        for up in node.get("upstream", []):
            if up not in nodes:
                errors.append(f"atlas:unknown_upstream:{nid}->{up}")

    def visit(nid: str, stack: tuple[str, ...]) -> None:
        if nid in stack:
            errors.append(f"atlas:cycle:{'->'.join(stack + (nid,))}")
            return
        for up in nodes.get(nid, {}).get("upstream", []):
            if up in nodes:
                visit(up, stack + (nid,))

    for nid in nodes:
        visit(nid, ())
    return sorted(set(errors))


def upstream_tree(nodes: dict[str, dict[str, Any]], nid: str, depth: int = 0) -> list[dict[str, Any]]:
    out = []
    for up in nodes[nid].get("upstream", []):
        n = nodes[up]
        out.append({"depth": depth + 1, "node_id": up, "name": n["name"], "status": n["status"],
                    "holders": [h["ticker"] for h in n["holders"]]})
        out.extend(upstream_tree(nodes, up, depth + 1))
    return out


def lookup_ticker(atlas: dict[str, Any], ticker: str) -> dict[str, Any]:
    nodes = index(atlas)
    t = norm(ticker)
    base = t.split(".")[0]
    hits = []
    for nid, node in nodes.items():
        for h in node["holders"]:
            ht = norm(h["ticker"])
            if ht == t or (ht.split(".")[0] == base and len(base) > 2):
                tree = upstream_tree(nodes, nid)
                next_hop = []
                for step in tree:
                    for hh in nodes[step["node_id"]]["holders"]:
                        if norm(hh["ticker"]) != ht:
                            next_hop.append({"ticker": hh["ticker"], "name": hh["name"], "node_id": step["node_id"],
                                             "node": step["name"], "status": step["status"], "depth": step["depth"],
                                             "basis": hh["basis"], "post_ids": hh.get("post_ids", [])})
                next_hop.sort(key=lambda x: (STATUS_RANK.get(x["status"], 9), x["depth"]))
                seen_t: set[str] = set()
                next_hop = [x for x in next_hop if not (norm(x["ticker"]) in seen_t or seen_t.add(norm(x["ticker"])))]
                downstream = [{"node_id": oid, "name": o["name"], "holders": [x["ticker"] for x in o["holders"]]}
                              for oid, o in nodes.items() if nid in o.get("upstream", [])]
                hits.append({
                    "chain_id": node["chain_id"], "chain": node["chain_name"], "node_id": nid, "node": node["name"],
                    "taxonomy": node["taxonomy"], "status": node["status"], "kind": node["kind"],
                    "archetypes": node.get("archetypes", []), "holder": h,
                    "peers": [x["ticker"] for x in node["holders"] if norm(x["ticker"]) != ht],
                    "upstream_path": tree, "downstream": downstream, "next_hop_candidates": next_hop,
                })
    return {"ticker": ticker, "atlas_as_of": atlas["as_of"], "found": bool(hits), "positions": hits,
            "note": "Atlas statuses are research leads as of atlas_as_of; verify with live data." if hits else
                    "Not in atlas: map the chain manually (PB-HUNT-08) and consider adding a node."}


def search_theme(atlas: dict[str, Any], keyword: str) -> list[dict[str, Any]]:
    k = keyword.lower()
    out = []
    for nid, node in index(atlas).items():
        hay = " ".join([node["chain_name"], node["name"], node["taxonomy"], node["chain_id"], nid] +
                       [h["name"] + " " + h["ticker"] + " " + h.get("role", "") for h in node["holders"]]).lower()
        if k in hay:
            out.append({"chain_id": node["chain_id"], "node_id": nid, "node": node["name"], "status": node["status"],
                        "holders": [h["ticker"] for h in node["holders"]]})
    return out


STATUS_ZH = {"now": "正在卡", "filling": "正在被订满", "coming": "即将", "monopoly_not_bottleneck": "垄断不紧缺",
             "diluted_exposure": "敞口稀释", "resolving": "缓解中", "not_bottleneck": "非瓶颈", "unknown": "未知"}


def render_md(atlas: dict[str, Any]) -> str:
    lines = ["# 卡点地图（Chokepoint Atlas）", "",
             f"> 由 `scripts/atlas.py render` 从 `assets/chokepoint-atlas.json` 生成，请勿手改。截至 {atlas['as_of']}。{atlas['disclaimer']}",
             "", "状态是档案期的研究判断（见 `references/serenity-doctrine.md` §2），使用前用实时数据复核。", ""]
    for chain in atlas["chains"]:
        lines += [f"## {chain['name']}（`{chain['chain_id']}`）", "", f"需求驱动：{chain.get('demand_driver', '—')}", "",
                  "| 节点 | 编码 | 状态 | 上游 | 原型 | 持有者 |", "|---|---|---|---|---|---|"]
        for n in chain["nodes"]:
            holders = "；".join(f"`{h['ticker']}` {h['name']}（{h.get('role', '')}，{h['basis']}）" for h in n["holders"])
            lines.append(f"| {n['name']} `{n['node_id']}` | {n['taxonomy']} | {STATUS_ZH[n['status']]}·{n['kind']} | "
                         f"{', '.join(n.get('upstream', [])) or '—'} | {', '.join(n.get('archetypes', []))} | {holders} |")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--atlas", type=Path, default=ATLAS_PATH)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    t = sub.add_parser("ticker")
    t.add_argument("ticker")
    th = sub.add_parser("theme")
    th.add_argument("keyword")
    pa = sub.add_parser("path")
    pa.add_argument("node_id")
    r = sub.add_parser("render")
    r.add_argument("--out", type=Path, default=MD_PATH)
    r.add_argument("--check", action="store_true", help="fail if the markdown is out of date")
    args = ap.parse_args(argv)
    atlas = load_atlas(args.atlas)
    if args.cmd == "validate":
        errs = validate(atlas)
        for e in errs:
            print(f"ERROR: {e}")
        if not errs:
            n = sum(len(c["nodes"]) for c in atlas["chains"])
            print(f"OK: atlas {atlas['atlas_version']} ({len(atlas['chains'])} chains, {n} nodes) is consistent")
        return 1 if errs else 0
    if args.cmd == "ticker":
        print(json.dumps(lookup_ticker(atlas, args.ticker), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "theme":
        print(json.dumps(search_theme(atlas, args.keyword), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "path":
        nodes = index(atlas)
        if args.node_id not in nodes:
            print(f"ERROR: unknown node {args.node_id}")
            return 1
        print(json.dumps(upstream_tree(nodes, args.node_id), ensure_ascii=False, indent=2))
        return 0
    text = render_md(atlas) + "\n"
    if args.check:
        current = args.out.read_text(encoding="utf-8") if args.out.exists() else ""
        if current != text:
            print(f"ERROR: {args.out} is out of date; run scripts/atlas.py render")
            return 1
        print(f"OK: {args.out} is up to date")
        return 0
    args.out.write_text(text, encoding="utf-8")
    print(f"OK: wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())