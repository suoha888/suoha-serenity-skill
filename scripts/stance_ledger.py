#!/usr/bin/env python3
"""Serenity memory layer (v5): stance extraction, point-in-time ledger, lookup.

Subcommands
  extract  Rule-based baseline: normalized posts JSONL -> StanceEvent JSONL.
           (For higher quality, have the host agent label posts with
           assets/stance-extraction-prompt.md and feed the same fold.)
  fold     StanceEvent JSONL -> per-ticker timeline JSON as of a cutoff.
  lookup   One ticker, point in time: what had Serenity said by --as-of?

Design choices:
  * Point-in-time: every fold/lookup uses only events with created_at <= as_of,
    so the ledger can be used for temporal-holdout evaluation without leakage.
  * DENY (explicitly not holding) is distinct from CLOSE (exited) and from
    silence (DORMANT). Silence never becomes a sell signal.
  * Conviction decays only after a grace period, with an explicit half-life,
    and the decayed value is reported next to the raw value.
  * Partitions never mix: subscription events are refused unless --allow-private.
  * Output carries post IDs, dates, labels and own-words summaries only; any
    verbatim text field is rejected.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ticker_normalizer import SEED_PATH, load_aliases, normalize  # noqa: E402

EXTRACTOR_VERSION = "rules-v6.1"
ACTION_WEIGHT = {  # conviction contribution of each action
    "OPEN": 0.55, "ADD": 0.7, "REAFFIRM": 0.65, "TRIM": 0.35, "WATCH": 0.25,
    "MENTION": 0.2, "BEARISH": 0.6, "CLOSE": 0.0, "DENY": 0.0,
}
# Ordered: first match wins. Patterns are deliberately conservative.
ACTION_CUES: list[tuple[str, str, re.Pattern[str]]] = [
    ("DENY", "explicit_no_position", re.compile(
        r"(i\s+(do\s+not|don'?t|no\s+longer)\s+(own|hold|have)|no\s+position|not\s+holding|i\s+have\s+no\s+(shares|position)|"
        r"不持有|没有持仓|没有仓位|未持有)", re.I)),
    ("CLOSE", "exit", re.compile(
        r"(sold\s+(all|everything|my\s+(entire|whole)?\s*position)|fully\s+exited|exited\s+(my|the)\s+position|closed\s+(my|the)\s+position|"
        r"i'?m\s+out\s+of|清仓|全部卖出)", re.I)),
    ("TRIM", "trim", re.compile(r"(\btrimm?ed\b|took\s+(some\s+)?profits?|sold\s+(some|a\s+portion|part)|减仓|止盈)", re.I)),
    ("ADD", "add", re.compile(r"(\badded\b|adding\s+(more|to)|bought\s+more|averag(ed|ing)\s+(up|down)|increas(ed|ing)\s+my\s+position|cost\s+averaged|加仓)", re.I)),
    ("OPEN", "open", re.compile(
        r"(initiated\s+a|opened\s+a\s+position|started\s+a\s+position|took\s+a\s+(\w+\s+)?position|went\s+long|i\s+(just\s+)?bought|"
        r"have\s+(very\s+)?small\s+exposure|i\s+(do\s+)?have\s+(a\s+)?(small\s+)?(position|exposure)|建仓|买入了)", re.I)),
    ("BEARISH", "bearish", re.compile(
        r"((i'?m|i\s+am|went|going|stay(ing)?)\s+short\b|\bshorting\b|short\s+position\s+in|bought\s+puts|(is|looks|are)\s+(extremely\s+|very\s+|so\s+)?(overvalued|overhyped)|"
        r"stay\s+away\s+from|i'?m\s+bearish|bearish\s+on|看空|做空)", re.I)),
    ("REAFFIRM", "reaffirm", re.compile(
        r"(not\s+selling|still\s+(holding|bullish|long)|my\s+(personal\s+)?favou?rite|once[- ]a[- ]generation|high\s+conviction|"
        r"conviction\s+(long|buy)|continue\s+to\s+hold|继续持有|坚定看好)", re.I)),
    ("WATCH", "watch", re.compile(r"(watchlist|watching|on\s+my\s+radar|keep(ing)?\s+an\s+eye|关注)", re.I)),
]
BULLISH_CUES = re.compile(
    r"(undervalued|compelling|bullish|upside|\d+x\b|moonshot|favou?rite|sleeper|beneficiar(y|ies)|\blong\b|go(es)?\s+brr|"
    r"cheap|re-?rate|mispriced|underpriced|chokepoint|bottleneck|monopoly|duopoly|sole\s+supplier|leading\s+supplier|"
    r"tailwind|catalyst|massive|huge|incredibl[ey]|strong(ly)?\s+(buy|positive)|highly\s+positive|winner|keys\s+of|"
    r"sold\s+out|accelerat|beat\b|raised\s+guidance|低估|看好|受益|卡脖子|瓶颈)", re.I)
BEARISH_CUES = re.compile(
    r"(overvalued|overhyped|bearish|dilut|\bATM\b|toxic|dumpster\s+fire|scam|fraud|grift|trapped|rangebound|"
    r"decelerat|bull\s+cycle\s+is\s+over|won'?t\s+translate|stay\s+away|bag\s*holders?|pump|dump|"
    r"\bshort(ing|ed)?\b|\bputs\b|downside|red\s+flag|高估|看空|稀释|割韭菜)", re.I)
CASHTAG = re.compile(r"\$([A-Za-z]{1,6}(?:\.[A-Za-z]{1,3})?)\b")
CODE_IN_PARENS = re.compile(r"\((\d{4,6}(?:\.[A-Za-z]{1,3})?)\)")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?。！？\n])\s+|\n+|\s->\s|\s-\s(?=[A-Z$])")
VERBATIM_FIELDS = {"text", "post_text", "tweet_text", "full_text", "raw_text"}


def parse_time(value: str) -> datetime:
    value = value.strip().replace("Z", "+00:00")
    if len(value) == 10:
        value += "T00:00:00+00:00"
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


_NAME_RX_CACHE: dict[int, tuple[re.Pattern[str] | None, dict[str, str]]] = {}


def _name_regex(aliases: dict[str, Any]) -> tuple[re.Pattern[str] | None, dict[str, str]]:
    key = id(aliases)
    if key not in _NAME_RX_CACHE:
        names: dict[str, str] = {}
        for row in aliases.values():
            for name in row.get("names", []):
                ascii_name = name.isascii()
                if (ascii_name and len(name) >= 4 and not name.isupper()) or (not ascii_name and len(name) >= 2):
                    names[name.lower()] = row["symbol"].split(".")[0] if row["symbol"].endswith((".US",)) else row["symbol"]
        if names:
            alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
            rx = re.compile(rf"(?<![A-Za-z]){alt}(?![A-Za-z])", re.I)
        else:
            rx = None
        _NAME_RX_CACHE[key] = (rx, names)
    return _NAME_RX_CACHE[key]


def tickers_in(text: str, aliases: dict[str, Any]) -> list[str]:
    found: list[str] = []
    rx, names = _name_regex(aliases)
    for m in CASHTAG.finditer(text):
        found.append(m.group(1).upper())
    for m in CODE_IN_PARENS.finditer(text):
        res = normalize(m.group(1), aliases)
        found.append(res["symbol"] or m.group(1))
    if rx is not None:
        for m in rx.finditer(text):
            found.append(names[m.group(0).lower()])
    # collapse a cashtag and its resolved foreign listing (e.g. SIVE and SIVE.ST)
    out: list[str] = []
    for t in dict.fromkeys(found):
        base = t.split(".")[0]
        if "." in t and base in out:
            out[out.index(base)] = t
        elif "." not in t and any(o.split(".")[0] == t for o in out):
            continue
        else:
            out.append(t)
    return out


def stance_of(sentence: str, action: str) -> str:
    if action in {"OPEN", "ADD", "REAFFIRM"}:
        return "bullish"
    if action == "BEARISH":
        return "bearish"
    bull = len(BULLISH_CUES.findall(sentence))
    bear = len(BEARISH_CUES.findall(sentence))
    if bull > bear:
        return "bullish"
    if bear > bull:
        return "bearish"
    return "neutral"


def extract_post(post: dict[str, Any], aliases: dict[str, Any]) -> list[dict[str, Any]]:
    text = post.get("text") or ""
    post_id = str(post.get("id") or post.get("post_id") or "")
    if not text or not re.fullmatch(r"[0-9]{5,25}", post_id):
        return []
    created = post.get("created_at")
    access = post.get("access_level", "public")
    partition = post.get("source_partition", access)
    events: dict[str, dict[str, Any]] = {}
    sentences = [s for s in SENTENCE_SPLIT.split(text) if s and s.strip()]
    whole_tickers = tickers_in(text, aliases)
    for sentence in sentences:
        sent_tickers = tickers_in(sentence, aliases)
        action, cue = "MENTION", "mention"
        for name, label, rx in ACTION_CUES:
            if rx.search(sentence):
                action, cue = name, label
                break
        # first-person action with no ticker in the sentence applies to a single-ticker post
        if not sent_tickers and action != "MENTION" and len(whole_tickers) == 1:
            sent_tickers = whole_tickers
        multi = len(sent_tickers) >= 2
        if multi and action == "BEARISH":
            # "copying shorts on $A to $B" is commentary about other traders, not a view on each name
            action, cue = "MENTION", "multi_ticker_ambiguous"
        stance = stance_of(sentence, action)
        if multi and action == "MENTION" and stance != "neutral":
            stance, cue = "neutral", "multi_ticker_ambiguous"  # lexicon cues cannot be assigned per ticker
        if stance == "neutral" and len(whole_tickers) == 1:
            stance = stance_of(text, action)
        for t in sent_tickers:
            conv = ACTION_WEIGHT[action]
            if action == "MENTION" and stance != "neutral":
                conv = 0.4
            if len(sent_tickers) > 3 and action not in {"DENY", "CLOSE"}:
                conv *= 0.6  # basket mentions carry less single-name conviction
            prev = events.get(t)
            rank = list(ACTION_WEIGHT).index
            if prev is not None and prev["action"] == action == "MENTION" and prev["stance"] == "neutral" and stance != "neutral":
                prev["stance"], prev["conviction"] = stance, round(conv, 3)
            if prev is None or (prev["action"] == "MENTION" and action != "MENTION") or (
                action in {"DENY", "CLOSE"} and prev["action"] not in {"DENY", "CLOSE"}
            ):
                events[t] = {
                    "schema_version": "5.0", "post_id": post_id, "created_at": created,
                    "ticker": t, "action": action, "stance": stance, "conviction": round(conv, 3), "cue": cue,
                    "is_reply": bool(post.get("is_reply", False)), "extractor": EXTRACTOR_VERSION,
                    "review_status": "machine", "access_level": access, "source_partition": partition,
                }
            _ = rank
    return list(events.values())


def _decayed(conv: float, days_silent: float, grace: float, half_life: float) -> float:
    if days_silent <= grace:
        return conv
    return conv * math.pow(0.5, (days_silent - grace) / half_life)


def fold(events: Iterable[dict[str, Any]], as_of: datetime, grace_days: float = 21,
         half_life_days: float = 45, dormant_days: float = 90, allow_private: bool = False,
         max_events: int = 12) -> dict[str, Any]:
    by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    skipped_future = skipped_private = 0
    for ev in events:
        bad = VERBATIM_FIELDS.intersection(ev)
        if bad:
            raise ValueError(f"verbatim field {sorted(bad)} in event {ev.get('post_id')}")
        if ev.get("source_partition", "public") not in {"public", "synthetic"} and not allow_private:
            skipped_private += 1
            continue
        if ev.get("review_status") == "rejected":
            continue
        when = parse_time(ev["created_at"])
        if when > as_of:
            skipped_future += 1
            continue
        by_ticker[ev["ticker"].upper()].append({**ev, "_t": when})
    tickers: dict[str, Any] = {}
    seen_times = [e["_t"] for evs in by_ticker.values() for e in evs]
    archive_through = max(seen_times).isoformat().replace("+00:00", "Z") if seen_times else None
    for t, evs in by_ticker.items():
        evs.sort(key=lambda e: (e["_t"], e["post_id"]))
        state, conv, holding = "WATCH", 0.0, "unknown"
        last_substantive = None
        for e in evs:
            a = e["action"]
            w = float(e.get("conviction", ACTION_WEIGHT[a]))
            if a in {"OPEN", "ADD"}:
                state, holding = "OPEN", "held"
                conv = min(1.0, max(conv, w) + (0.1 if a == "ADD" and conv > 0 else 0))
            elif a == "REAFFIRM":
                state = "OPEN" if state in {"OPEN", "DORMANT"} else "BULLISH"
                conv = min(1.0, max(conv, w) + 0.05)
            elif a == "TRIM":
                conv = max(0.15, conv - 0.2)
            elif a == "CLOSE":
                state, holding, conv = "CLOSED", "cleared", 0.0
            elif a == "DENY":
                state, holding = "DENIED", "denied"
                conv = min(conv, 0.3)
            elif a == "BEARISH":
                if holding == "held" and state in {"OPEN", "DORMANT"}:
                    conv = max(0.15, conv - 0.15)  # a holder's bearish aside is not an exit
                else:
                    state, conv = "BEARISH", max(conv, w) if state == "BEARISH" else w
            elif a == "WATCH" and state in {"WATCH"}:
                conv = max(conv, w)
            elif a == "MENTION":
                st = e.get("stance", "neutral")
                if st == "bullish":
                    if state in {"WATCH", "BEARISH", "CLOSED", "DENIED"}:
                        state = "BULLISH" if state != "DENIED" else "DENIED"
                    conv = max(conv, w) if state != "OPEN" else min(1.0, conv + 0.02)
                elif st == "bearish":
                    if holding == "held" and state in {"OPEN", "DORMANT"}:
                        conv = max(0.15, conv - 0.05)
                    elif state != "DENIED":
                        state, conv = "BEARISH", max(w, 0.4)
                elif state == "WATCH":
                    conv = max(conv, w)
            if a != "MENTION" or e.get("stance", "neutral") != "neutral":
                last_substantive = e
        last = evs[-1]
        days_silent = (as_of - last["_t"]).total_seconds() / 86400
        eff = _decayed(conv, days_silent, grace_days, half_life_days)
        shown_state = state
        if state in {"OPEN", "BULLISH"} and days_silent >= dormant_days:
            shown_state = "DORMANT"
        mention_90 = sum(1 for e in evs if (as_of - e["_t"]).days <= 90)
        if shown_state in {"OPEN", "BULLISH"}:
            bucket = "CORE" if eff >= 0.7 and mention_90 >= 5 else "MEDIUM" if eff >= 0.5 else "STARTER"
        else:
            bucket = "WATCH" if shown_state in {"WATCH", "DORMANT"} else "NONE"
        material = [e for e in evs if e["action"] != "MENTION" or e.get("stance", "neutral") != "neutral"] or evs
        timeline = [
            {k: v for k, v in {
                "date": e["_t"].date().isoformat(), "post_id": e["post_id"], "action": e["action"],
                "stance": e.get("stance"),
                "conviction": round(float(e.get("conviction", 0)), 3), "summary": e.get("summary"),
            }.items() if v is not None}
            for e in material[-max_events:]
        ]
        tickers[t] = {
            "ticker": t, "state": shown_state, "holding_status": holding,
            "raw_conviction": round(conv, 3), "effective_conviction": round(eff, 3), "bucket": bucket,
            "first_mention": evs[0]["_t"].date().isoformat(), "last_mention": last["_t"].date().isoformat(),
            "last_substantive": last_substantive["_t"].date().isoformat() if last_substantive else None,
            "days_since_last_mention": round(days_silent, 1), "mention_count": len(evs),
            "mentions_last_90d": mention_90, "timeline": timeline,
        }
    return {
        "schema_version": "5.0", "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "archive_through": archive_through, "extractor": EXTRACTOR_VERSION,
        "params": {"grace_days": grace_days, "half_life_days": half_life_days, "dormant_days": dormant_days},
        "skipped_future_events": skipped_future, "skipped_private_events": skipped_private,
        "ticker_count": len(tickers), "tickers": dict(sorted(tickers.items())),
    }


def lens_memory(ledger: dict[str, Any], ticker: str) -> dict[str, Any]:
    """Shape one ledger entry as a SerenityLens.serenity_memory block."""
    row = ledger["tickers"].get(ticker.upper())
    through = ledger.get("archive_through") or ledger["as_of"]
    if not row:
        return {"status": "no_mentions", "source": "stance_ledger", "archive_through": through, "note":
                f"No mention of {ticker.upper()} in the local Serenity archive (covers posts through {through[:10]}). "
                "Absence is not a negative view."}
    return {
        "status": "available", "source": "stance_ledger", "current_state": row["state"],
        "first_mention": row["first_mention"], "last_mention": row["last_mention"],
        "mention_count": row["mention_count"], "timeline": row["timeline"],
        "archive_through": through,
        "note": (f"Point-in-time as of {ledger['as_of']}; archive covers posts through {through[:10]} "
                 f"(silence after that date is unknown, not a sell); holding_status={row['holding_status']}, "
                 f"effective conviction {row['effective_conviction']} (raw {row['raw_conviction']}). "
                 "Serenity statements are leads, not company facts."),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("extract")
    ex.add_argument("posts", type=Path, help="normalized posts JSONL (id, text, created_at, ...)")
    ex.add_argument("--out", type=Path, required=True)
    ex.add_argument("--aliases", type=Path, action="append", default=[])
    for name in ("fold", "lookup"):
        sp = sub.add_parser(name)
        sp.add_argument("events", type=Path, help="StanceEvent JSONL")
        sp.add_argument("--as-of", required=True)
        sp.add_argument("--grace-days", type=float, default=21)
        sp.add_argument("--half-life-days", type=float, default=45)
        sp.add_argument("--dormant-days", type=float, default=90)
        sp.add_argument("--allow-private", action="store_true")
        if name == "fold":
            sp.add_argument("--out", type=Path, required=True)
        else:
            sp.add_argument("--ticker", required=True)
            sp.add_argument("--lens-memory", action="store_true", help="emit a SerenityLens serenity_memory block")
    args = p.parse_args(argv)
    if args.cmd == "extract":
        aliases = load_aliases([*args.aliases, SEED_PATH])
        n_posts = n_events = 0
        with args.out.open("w", encoding="utf-8") as fh:
            for post in read_jsonl(args.posts):
                n_posts += 1
                for ev in extract_post(post, aliases):
                    n_events += 1
                    fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        print(f"OK: {n_posts} posts -> {n_events} stance events ({EXTRACTOR_VERSION}) at {args.out}")
        return 0
    ledger = fold(read_jsonl(args.events), parse_time(args.as_of), args.grace_days,
                  args.half_life_days, args.dormant_days, args.allow_private)
    if args.cmd == "fold":
        args.out.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK: {ledger['ticker_count']} tickers as of {ledger['as_of']} -> {args.out} "
              f"(ignored {ledger['skipped_future_events']} future, {ledger['skipped_private_events']} private events)")
        return 0
    out = lens_memory(ledger, args.ticker) if args.lens_memory else ledger["tickers"].get(args.ticker.upper(), {"ticker": args.ticker.upper(), "state": "NO_MENTIONS"})
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
