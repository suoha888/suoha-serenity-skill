#!/usr/bin/env python3
"""Public Serenity stance timeline: paraphrased summaries of PUBLIC posts + post ids.

  show <TICKER> [--as-of YYYY-MM-DD] [--recent N]   print a thesis dossier (Markdown)
  memory <TICKER> [--as-of YYYY-MM-DD]              print a SerenityLens serenity_memory block (JSON)
  list [--top N]                                    tickers with the most public entries

Data: assets/serenity-public-timeline.json (built offline from the maintainer's archive; only our own
Chinese paraphrases and public post ids are shipped, never original text or subscription content).
A stance here is what a public post expressed at that time, not a position record; silence is not a sell.
Framework research only; not Serenity's own words and not investment advice.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "assets" / "serenity-public-timeline.json"
STANCE_ZH = {"bull": "看多", "bull_speculative": "看多（投机）", "bear": "看空", "avoid": "回避", "neutral": "中性",
             "watch": "观察", "downgrade": "下调", "trim": "减仓", "correction": "更正"}
ACTION = {"bull": "REAFFIRM", "bull_speculative": "REAFFIRM", "bear": "BEARISH", "avoid": "BEARISH", "trim": "TRIM",
          "downgrade": "TRIM", "watch": "WATCH", "neutral": "MENTION", "correction": "MENTION"}
LENS_STANCE = {"bull": "bullish", "bull_speculative": "bullish", "bear": "bearish", "avoid": "bearish", "trim": "neutral",
               "downgrade": "neutral", "watch": "neutral", "neutral": "neutral", "correction": "neutral"}
THESIS_TYPES = {"thesis", "thesis_summary", "chokepoint", "bottleneck", "supply_chain", "thesis_update", "mispricing"}
RISK_TYPES = {"risk", "dilution", "not_adopted", "retrospective", "track_record", "discipline"}
URL = "https://x.com/aleabitoreddit/status/{}"


def load(path: Path = ASSET) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(data: dict[str, Any], ticker: str) -> str | None:
    t = data["tickers"]
    raw = ticker.strip()
    for k in (raw, raw.upper()):
        if k in t:
            return k
    try:  # alias table: SIVEF -> SIVE.ST, 海力士 -> 000660.KS ...
        sys.path.insert(0, str(ROOT / "scripts"))
        import ticker_normalizer as tn  # type: ignore
        sym = tn.normalize(raw, tn.load_aliases([ROOT / "assets" / "ticker-aliases.seed.json"])).get("symbol")
        if sym and sym in t:
            return sym
    except Exception:  # noqa: BLE001 - lookup must never crash a report
        pass
    base = raw.upper().split(".")[0]
    hits = [k for k in t if k.upper().split(".")[0] == base]
    return hits[0] if len(hits) == 1 else None


def entries(data: dict[str, Any], key: str, as_of: str | None = None, incidental: bool = False) -> list[dict[str, Any]]:
    """Point-in-time rows. Rows flagged x=1 only list this ticker next to the company the post is about
    (e.g. a ten-name sector list); they are excluded unless incidental=True and never count as a stance."""
    return [e for e in data["tickers"].get(key, []) if (not as_of or e["d"] <= as_of[:10]) and bool(e.get("x")) == incidental]


def directional(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Neutral cards are context (method, background, news), not a change of view."""
    return [e for e in rows if e["s"] != "neutral"] or rows


def changes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out, last = [], None
    for e in directional(rows):
        if e["s"] != last:
            out.append(e)
            last = e["s"]
    return out


def memory(ticker: str, as_of: str | None = None, data: dict[str, Any] | None = None) -> dict[str, Any]:
    data = data or load()
    through = min(data["archive_through"], as_of[:10]) if as_of else data["archive_through"]
    key = resolve(data, ticker)
    rows = entries(data, key, as_of) if key else []
    side = len(entries(data, key, as_of, incidental=True)) if key else 0
    if not rows:
        extra = f"另有 {side} 条只是和其他公司一起被列出，不算表态。" if side else ""
        return {"status": "no_mentions", "source": "public_timeline", "archive_through": through, "incidental_count": side,
                "note": f"公开时间线里没有关于 {ticker.upper()} 本身的表态（覆盖至 {through}）。{extra}没提到不代表看空。"}
    picked = changes(rows)
    picked = (picked[:4] + picked[-7:]) if len(picked) > 11 else picked
    cur = directional(rows)[-1]
    if cur not in picked:
        picked.append(cur)
    tl = [{"date": e["d"], "post_id": e["p"][0], "action": ACTION[e["s"]], "stance": LENS_STANCE[e["s"]],
           "summary": e["c"][:160]} for e in picked[-12:]]
    return {"status": "available", "source": "public_timeline", "current_state": cur["s"],
            "first_mention": rows[0]["d"], "last_mention": rows[-1]["d"], "mention_count": len(rows),
            "incidental_count": side,
            "timeline": tl, "archive_through": through,
            "note": ("公开帖转述（不是原话，不含订阅内容），帖子编号可在 x.com 查原文。立场 = 当时公开表达的看法，不是持仓记录；"
                     f"{through} 之后是否有新表态未知（沉默不等于卖出）。Serenity 的说法是线索，不是公司事实。")}


def dossier(ticker: str, as_of: str | None = None, recent: int = 10, data: dict[str, Any] | None = None) -> str:
    data = data or load()
    key = resolve(data, ticker)
    rows = entries(data, key, as_of) if key else []
    side = len(entries(data, key, as_of, incidental=True)) if key else 0
    if not rows:
        extra = f"另有 {side} 条只是和其他公司一起被列出（不算表态）。" if side else ""
        return f"# {ticker.upper()}：公开时间线无记录\n\n覆盖至 {data['archive_through']}。{extra}没提到不代表看空。\n"
    dist = collections.Counter(STANCE_ZH[e["s"]] for e in rows)
    ch = changes(rows)
    L = [f"# {key} · Serenity 公开言论档案（转述）", "",
         f"- 公开条目 {len(rows)} 条" + (f"（另有 {side} 条只是和其他公司一起被列出，不计入）" if side else "") + f" · {rows[0]['d']} → {rows[-1]['d']} · 最近的方向性表态：**{STANCE_ZH[directional(rows)[-1]['s']]}**（{directional(rows)[-1]['d']}）",
         "- 立场分布：" + "，".join(f"{k} {v}" for k, v in dist.most_common()),
         "- 方向性立场变化（不含中性/背景条目）：" + " → ".join(f"{e['d']} {STANCE_ZH[e['s']]}" for e in ch[-15:]) + (" …（只显示最近 15 次）" if len(ch) > 15 else ""), ""]

    def block(title: str, items: list[dict[str, Any]], n: int) -> None:
        if not items:
            return
        L.extend([f"## {title}", ""])
        for e in items[-n:]:
            L.append(f"- {e['d']} [{STANCE_ZH[e['s']]}] {e['c']}（帖 {', '.join(e['p'][:2])}）")
        L.append("")

    block("核心论点（卡点/瓶颈/论点更新）", [e for e in rows if e["t"] in THESIS_TYPES], 8)
    kpis = list(dict.fromkeys(e["kpi"] for e in rows if e.get("kpi") and len(e["kpi"]) >= 4 and not e["kpi"].startswith("各")))
    if kpis:
        L.extend(["## 他盯的 KPI", ""] + [f"- {k}" for k in kpis[-10:]] + [""])
    flips = list(dict.fromkeys(e["flip"] for e in rows if e.get("flip")))
    if flips:
        L.extend(["## 论点失效条件（他说过什么情况下会改变看法）", ""] + [f"- {k}" for k in flips[-10:]] + [""])
    block("风险 / 稀释 / 回顾", [e for e in rows if e["t"] in RISK_TYPES or e["s"] in {"bear", "avoid", "trim", "downgrade", "correction"}], 10)
    block(f"最近 {recent} 条", rows, recent)
    L.append(f"> 以上为公开帖转述，不是原话；Serenity 主页：https://x.com/aleabitoreddit ，原帖：{URL.format('<编号>')}。立场 = 当时的公开表达，不是持仓记录；"
             f"覆盖至 {data['archive_through']}，之后的表态未知。框架研究用途，不代表 Serenity 本人观点，也不是投资建议。")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("show", "memory"):
        s = sub.add_parser(name)
        s.add_argument("ticker")
        s.add_argument("--as-of", help="point-in-time cutoff YYYY-MM-DD (backtests)")
        if name == "show":
            s.add_argument("--recent", type=int, default=10)
    ls = sub.add_parser("list")
    ls.add_argument("--top", type=int, default=40)
    a = p.parse_args(argv)
    if a.cmd == "show":
        print(dossier(a.ticker, a.as_of, a.recent))
    elif a.cmd == "memory":
        print(json.dumps(memory(a.ticker, a.as_of), ensure_ascii=False, indent=2))
    else:
        d = load()
        main_rows = {k: [e for e in v if not e.get("x")] for k, v in d["tickers"].items()}
        for k, v in sorted(((k, v) for k, v in main_rows.items() if v), key=lambda kv: -len(kv[1]))[:a.top]:
            print(f"{k}\t{len(v)}\t{v[0]['d']} → {v[-1]['d']}\t{STANCE_ZH[directional(v)[-1]['s']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
