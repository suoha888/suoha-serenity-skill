#!/usr/bin/env python3
"""Look-ahead-safe forward returns for dated signals (v5), network-free.

Input
  signals JSONL: {"signal_id", "ticker", "created_at", ...}
  prices dir:    <TICKER>.csv with header date,open,high,low,close[,adj_close]
                 (any order; extra columns ignored). When adj_close and close are
                 both present, high/low are scaled by adj_close/close so every
                 number is on the same split/dividend-adjusted basis (v8.2).

Entry rule (default --entry next_close): the close of the first trading day
strictly AFTER the post date. Anchoring on the same-day close when a post
lands after the bell silently leaks the market reaction into the entry price. --entry same_close reproduces that convention when you
need a like-for-like comparison.

Output per signal: entry date/close, D1/D3/D7/D30 trading-day returns and,
within --window trading days after entry:
  max_runup_pct     highest intraday high vs the entry close
  max_adverse_pct   lowest intraday low vs the entry close (worst point if you
                    bought at entry; called max_drawdown_pct before v8.2)
  max_drawdown_pct  true peak-to-trough drop of the adjusted close path,
                    starting from the entry close (a stock can rise 80% and then
                    fall 40% from that peak while never trading below entry)
and the return to the last available close. Missing data is reported, never filled.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

HORIZONS = (1, 3, 7, 30)


def load_prices(path: Path) -> list[tuple[date, float, float, float]]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            r = {k.strip().lower(): v for k, v in r.items() if k}
            try:
                d = date.fromisoformat(r["date"][:10])
                adj = r.get("adj_close") or r.get("adj close")
                raw = r.get("close")
                close = float(adj or raw)
                k = close / float(raw) if adj and raw and float(raw) else 1.0  # put raw high/low on the adjusted basis
                high = float(r["high"]) * k if r.get("high") else close
                low = float(r["low"]) * k if r.get("low") else close
            except (KeyError, ValueError):
                continue
            rows.append((d, high, low, close))
    rows.sort()
    return rows


def evaluate(signal: dict[str, Any], prices: list[tuple[date, float, float, float]],
             entry: str = "next_close", window: int = 60) -> dict[str, Any]:
    out: dict[str, Any] = {k: signal.get(k) for k in ("signal_id", "ticker", "created_at")}
    if not prices:
        return {**out, "status": "no_price_data"}
    d0 = date.fromisoformat(str(signal["created_at"])[:10])
    if entry == "same_close":
        idx = next((i for i, r in enumerate(prices) if r[0] >= d0), None)
    else:
        idx = next((i for i, r in enumerate(prices) if r[0] > d0), None)
    if idx is None:
        return {**out, "status": "no_entry_bar"}
    e_date, _, _, e_close = prices[idx]
    out.update(status="ok", entry_rule=entry, entry_date=e_date.isoformat(), entry_close=e_close)
    for h in HORIZONS:
        j = idx + h
        out[f"d{h}_return_pct"] = round((prices[j][3] / e_close - 1) * 100, 3) if j < len(prices) else None
    seg = prices[idx + 1: idx + 1 + window]
    if seg:
        out["max_runup_pct"] = round((max(r[1] for r in seg) / e_close - 1) * 100, 3)
        out["max_adverse_pct"] = round((min(r[2] for r in seg) / e_close - 1) * 100, 3)
        peak, mdd = e_close, 0.0
        for r in seg:
            peak = max(peak, r[3])
            mdd = min(mdd, r[3] / peak - 1)
        out["max_drawdown_pct"] = round(mdd * 100, 3)
        out["window_trading_days"] = len(seg)
    out["return_to_last_pct"] = round((prices[-1][3] / e_close - 1) * 100, 3)
    out["last_date"] = prices[-1][0].isoformat()
    return out


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in rows if r.get("status") == "ok"]
    summary: dict[str, Any] = {"signals": len(rows), "evaluated": len(ok)}
    for key in [f"d{h}_return_pct" for h in HORIZONS] + ["max_runup_pct", "max_adverse_pct", "max_drawdown_pct"]:
        vals = sorted(r[key] for r in ok if r.get(key) is not None)
        if vals:
            mid = len(vals) // 2
            median = vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2
            summary[key] = {"n": len(vals), "median": round(median, 3),
                            "hit_rate_gt0": round(sum(v > 0 for v in vals) / len(vals), 3)}
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("signals", type=Path)
    p.add_argument("--prices-dir", type=Path, required=True)
    p.add_argument("--entry", choices=["next_close", "same_close"], default="next_close")
    p.add_argument("--window", type=int, default=60)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    cache: dict[str, list] = {}
    rows = []
    for line in args.signals.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sig = json.loads(line)
        t = str(sig["ticker"])
        if t not in cache:
            f = args.prices_dir / f"{t}.csv"
            cache[t] = load_prices(f) if f.is_file() else []
        rows.append(evaluate(sig, cache[t], args.entry, args.window))
    result = {"schema_version": "5.0", "entry_rule": args.entry, "summary": summarize(rows), "rows": rows}
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {result['summary']['evaluated']}/{len(rows)} signals evaluated -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
