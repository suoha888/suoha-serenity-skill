#!/usr/bin/env python3
"""Serenity alignment benchmark (v5): grade a skill against Serenity's own
later judgments, point in time, with no leakage.  Network-free.

Subcommands
  make-cases   From a StanceEvent JSONL, build blind cases: for each ticker the
               author later turned bullish/bearish on, ask about it --lead-days
               BEFORE that first call, using only information before as_of.
               Writes cases.jsonl (public question) and answers.jsonl (sealed).
  score        Compare one or more prediction files with the sealed answers.
               Reports accuracy, bullish precision/recall, Brier score, and
               coverage per system, so several systems can be ranked blind.
  agreement    Compare two stance label sets per (post_id, ticker), e.g. the
               rule baseline vs an LLM extraction vs a reviewer's labels.

Prediction line: {"case_id", "stance": bullish|bearish|neutral, "confidence": 0..1}
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stance_ledger import parse_time, read_jsonl  # noqa: E402

BULL_ACTIONS = {"OPEN", "ADD", "REAFFIRM"}


def event_stance(ev: dict[str, Any]) -> str:
    if ev["action"] in BULL_ACTIONS:
        return "bullish"
    if ev["action"] in {"BEARISH"}:
        return "bearish"
    return ev.get("stance", "neutral")


def make_cases(events: list[dict[str, Any]], lead_days: int, horizon_days: int,
               min_events: int, seed: int, negatives: int) -> tuple[list[dict], list[dict]]:
    by_t: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in events:
        if e.get("source_partition", "public") in {"public", "synthetic"}:
            by_t[e["ticker"]].append({**e, "_t": parse_time(e["created_at"])})
    cases, answers = [], []
    rng = random.Random(seed)
    for t, evs in sorted(by_t.items()):
        evs.sort(key=lambda e: e["_t"])
        decided = [e for e in evs if event_stance(e) != "neutral"]
        if len(decided) < min_events:
            continue
        first = decided[0]
        as_of = first["_t"] - timedelta(days=lead_days)
        prior = [e for e in evs if e["_t"] <= as_of]
        if any(event_stance(e) != "neutral" for e in prior):
            continue  # already decided before the case date -> not a blind call
        window = [e for e in decided if first["_t"] <= e["_t"] <= first["_t"] + timedelta(days=horizon_days)]
        votes = Counter(event_stance(e) for e in window)
        label = votes.most_common(1)[0][0]
        cid = f"case:{t}:{as_of.date().isoformat()}"
        cases.append({"case_id": cid, "ticker": t, "as_of": as_of.isoformat().replace("+00:00", "Z"),
                      "question": f"As of {as_of.date()}, would a Serenity-style chokepoint analysis be bullish, bearish or neutral on {t}?"})
        answers.append({"case_id": cid, "label": label, "first_call_post_id": first["post_id"],
                        "first_call_date": first["_t"].date().isoformat(), "support": dict(votes)})
    if negatives:
        neutral_t = [t for t, evs in by_t.items() if all(event_stance(e) == "neutral" for e in evs)]
        for t in rng.sample(neutral_t, min(negatives, len(neutral_t))):
            evs = sorted(by_t[t], key=lambda e: e["_t"])
            as_of = evs[0]["_t"]
            cid = f"case:{t}:{as_of.date().isoformat()}"
            cases.append({"case_id": cid, "ticker": t, "as_of": as_of.isoformat().replace("+00:00", "Z"),
                          "question": f"As of {as_of.date()}, would a Serenity-style chokepoint analysis be bullish, bearish or neutral on {t}?"})
            answers.append({"case_id": cid, "label": "neutral", "support": {"neutral": len(evs)}})
    order = list(range(len(cases)))
    rng.shuffle(order)
    return [cases[i] for i in order], [answers[i] for i in order]


def score(answers: dict[str, dict], preds: dict[str, dict]) -> dict[str, Any]:
    n = len(answers)
    covered = [cid for cid in answers if cid in preds]
    correct = sum(preds[c]["stance"] == answers[c]["label"] for c in covered)
    tp = sum(1 for c in covered if preds[c]["stance"] == "bullish" and answers[c]["label"] == "bullish")
    pp = sum(1 for c in covered if preds[c]["stance"] == "bullish")
    ap = sum(1 for c in answers if answers[c]["label"] == "bullish")
    brier_terms = []
    for c in covered:
        p_bull = float(preds[c].get("confidence", 0.5)) if preds[c]["stance"] == "bullish" else 1 - float(preds[c].get("confidence", 0.5))
        brier_terms.append((p_bull - (1.0 if answers[c]["label"] == "bullish" else 0.0)) ** 2)
    return {
        "cases": n, "coverage": round(len(covered) / n, 3) if n else 0.0,
        "accuracy": round(correct / len(covered), 3) if covered else None,
        "bullish_precision": round(tp / pp, 3) if pp else None,
        "bullish_recall": round(tp / ap, 3) if ap else None,
        "brier_bullish": round(sum(brier_terms) / len(brier_terms), 4) if brier_terms else None,
    }


def agreement(a: list[dict], b: list[dict]) -> dict[str, Any]:
    def key(e):
        return (str(e["post_id"]), str(e["ticker"]).upper().split(".")[0])
    A = {key(e): event_stance(e) if "action" in e else e["stance"] for e in a}
    B = {key(e): event_stance(e) if "action" in e else e["stance"] for e in b}
    common = sorted(set(A) & set(B))
    decided = [k for k in common if A[k] != "neutral" and B[k] != "neutral"]
    return {
        "a_pairs": len(A), "b_pairs": len(B), "common_pairs": len(common),
        "b_recall_in_a": round(len(common) / len(B), 3) if B else None,
        "agreement_all": round(sum(A[k] == B[k] for k in common) / len(common), 3) if common else None,
        "agreement_when_both_decided": round(sum(A[k] == B[k] for k in decided) / len(decided), 3) if decided else None,
        "confusion": {f"{x}->{y}": c for (x, y), c in Counter((A[k], B[k]) for k in common).most_common()},
    }


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return list(read_jsonl(path))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make-cases")
    mk.add_argument("events", type=Path)
    mk.add_argument("--out-dir", type=Path, required=True)
    mk.add_argument("--lead-days", type=int, default=14)
    mk.add_argument("--horizon-days", type=int, default=60)
    mk.add_argument("--min-events", type=int, default=2)
    mk.add_argument("--negatives", type=int, default=0)
    mk.add_argument("--seed", type=int, default=7)
    sc = sub.add_parser("score")
    sc.add_argument("answers", type=Path)
    sc.add_argument("predictions", type=Path, nargs="+")
    ag = sub.add_parser("agreement")
    ag.add_argument("a", type=Path)
    ag.add_argument("b", type=Path)
    args = p.parse_args(argv)
    if args.cmd == "make-cases":
        cases, answers = make_cases(_jsonl(args.events), args.lead_days, args.horizon_days,
                                    args.min_events, args.seed, args.negatives)
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "cases.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), encoding="utf-8")
        (args.out_dir / "answers.sealed.jsonl").write_text("".join(json.dumps(a, ensure_ascii=False) + "\n" for a in answers), encoding="utf-8")
        print(f"OK: {len(cases)} blind cases; labels {dict(Counter(a['label'] for a in answers))}; answers sealed separately")
        return 0
    if args.cmd == "score":
        answers = {a["case_id"]: a for a in _jsonl(args.answers)}
        board = {}
        for path in args.predictions:
            preds = {x["case_id"]: x for x in _jsonl(path)}
            board[path.stem] = score(answers, preds)
        print(json.dumps({"leaderboard": board}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(agreement(_jsonl(args.a), _jsonl(args.b)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
