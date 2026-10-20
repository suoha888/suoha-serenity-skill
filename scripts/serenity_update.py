#!/usr/bin/env python3
"""Keep the Serenity framework current without leaking post text (v6.1).

Serenity's posts stay in a PRIVATE archive (outside this repo, or in a private
repo).  The public skill repo only receives post IDs, counts, and the
maintainer's own-words summaries.  Subcommands:

  ingest   Merge new posts (JSONL / JSON array / X export) into the private
           archive: normalise fields, de-duplicate by post ID, sort by time.
  refresh  Re-extract stance events from the archive (stance_ledger rules) and
           write the PUBLIC manifest assets/serenity-archive-manifest.json
           (counts, date range, per-month volume, ticker mention counts,
           extractor version - never text).
  gaps     Private review queue: tickers Serenity mentioned that the atlas
           does not cover, and post IDs per doctrine keyword family since a
           date - the maintainer turns these into own-words cards/nodes.
  check    Leak guard: scan every public file for long word n-grams copied
           from the archive.  Run before every push (exit 1 on a hit).
  install-hook  Write a git pre-push hook that runs `check`.

Typical update (see references/serenity-update-workflow.md):
  export SERENITY_PRIVATE_DIR=~/serenity-private
  python scripts/serenity_update.py ingest new_posts.jsonl
  python scripts/serenity_update.py refresh
  python scripts/serenity_update.py gaps --since 2026-06-05
  # ... write own-words cards / atlas nodes with post IDs ...
  python scripts/serenity_update.py check && git push
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stance_ledger import EXTRACTOR_VERSION, extract_post, tickers_in  # noqa: E402
from ticker_normalizer import SEED_PATH, load_aliases  # noqa: E402

MANIFEST_PATH = ROOT / "assets" / "serenity-archive-manifest.json"
TEXT_SUFFIXES = {".md", ".json", ".jsonl", ".py", ".html", ".txt", ".yaml", ".yml", ".csv", ".toml"}
POST_ID_RE = re.compile(r"^[0-9]{5,25}$")
FAMILIES = {  # doctrine keyword families -> which reference a new post may update
    "pricing_power": r"price (?:hike|increase)s?|raised prices|pricing power|涨价|提价",
    "capacity_signal": r"sold out|lead times?|allocation|capacity (?:constrained|reservation)|prepay|take[- ]or[- ]pay|订满|产能",
    "new_chokepoint": r"bottleneck|chokepoint|choke point|sole (?:source|supplier)|only (?:supplier|company)|卡点|瓶颈",
    "dilution_financing": r"\bATM\b|dilut\w*|offering|warrants?|稀释|增发",
    "valuation_asymmetry": r"undervalued|mispriced|asymmetr\w*|\b\d{1,3}x\b|低估",
    "position_change": r"\b(?:sold|trimmed|exited|added|bought|initiated)\b|清仓|减仓|加仓|建仓",
    "self_correction": r"i was wrong|my mistake|mistake|lesson|看错|教训",
}


def private_dir(arg: str | None) -> Path:
    d = Path(arg or os.environ.get("SERENITY_PRIVATE_DIR") or Path.home() / ".serenity-private").expanduser()
    return d


def guard_private_path(path: Path) -> None:
    """Refuse a private archive that git would publish from this repo."""
    path = path.resolve()
    try:
        path.relative_to(ROOT)
    except ValueError:
        return  # outside the public repo: fine
    res = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", str(path)], capture_output=True)
    if res.returncode != 0:
        raise SystemExit(f"refusing: {path} is inside the public repo and NOT git-ignored. "
                         "Keep Serenity's post text outside the repo (or in a private repo).")


def parse_created(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        ts = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z")
    v = str(value).strip()
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(v)  # "Wed Oct 10 20:19:24 +0000 2018" style
        except (TypeError, ValueError):
            try:
                dt = datetime.strptime(v, "%a %b %d %H:%M:%S %z %Y")
            except ValueError:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalise(raw: dict[str, Any]) -> dict[str, Any] | None:
    raw = raw.get("tweet", raw) if isinstance(raw.get("tweet"), dict) else raw  # X archive export wrapper
    pid = str(raw.get("id") or raw.get("id_str") or raw.get("post_id") or raw.get("rest_id") or "").strip()
    text = raw.get("text") or raw.get("full_text") or raw.get("note_tweet_text") or ""
    created = parse_created(raw.get("created_at") or raw.get("createdAt") or raw.get("date"))
    if not POST_ID_RE.match(pid) or not text or not created:
        return None
    out = {"id": pid, "text": text, "created_at": created}
    for k in ("is_reply", "lang", "url", "access_level", "source_partition", "conversation_id", "in_reply_to_status_id"):
        if raw.get(k) not in (None, ""):
            out[k] = raw[k]
    out.setdefault("access_level", "public")
    return out


def read_any(path: Path) -> Iterable[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".js" and "=" in text[:200]:  # X export: window.YTD.tweets.part0 = [...]
        text = text.split("=", 1)[1]
    stripped = text.lstrip()
    if stripped.startswith("["):
        yield from json.loads(stripped)
        return
    # split on "\n" only: post text may contain U+2028/U+2029, which str.splitlines() treats as line breaks
    for n, line in enumerate(text.split("\n"), 1):
        if line.strip():
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{n}: not JSON ({exc})")


def load_archive(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {p["id"]: p for p in (normalise(r) for r in read_any(path)) if p}


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def cmd_ingest(args: argparse.Namespace) -> int:
    archive = Path(args.archive) if args.archive else private_dir(args.private_dir) / "posts.jsonl"
    guard_private_path(archive)
    posts = load_archive(archive)
    before = len(posts)
    added = updated = rejected = 0
    for src in args.inputs:
        for raw in read_any(Path(src)):
            p = normalise(raw) if isinstance(raw, dict) else None
            if not p:
                rejected += 1
                continue
            if p["id"] in posts:
                if posts[p["id"]].get("text") != p["text"] and len(p["text"]) >= len(posts[p["id"]]["text"]):
                    posts[p["id"]] = {**posts[p["id"]], **p}  # longer/edited version wins (note tweets)
                    updated += 1
                continue
            posts[p["id"]] = p
            added += 1
    rows = sorted(posts.values(), key=lambda r: (r["created_at"], r["id"]))
    write_jsonl(archive, rows)
    print(json.dumps({"archive": str(archive), "before": before, "added": added, "updated": updated,
                      "rejected": rejected, "total": len(rows),
                      "last_post": rows[-1]["created_at"] if rows else None}, ensure_ascii=False))
    return 0


def build_manifest(posts: list[dict[str, Any]], events: list[dict[str, Any]], atlas_tickers: set[str]) -> dict[str, Any]:
    months = Counter(p["created_at"][:7] for p in posts)
    mentions = Counter(e["ticker"] for e in events)
    actions = Counter(e["action"] for e in events)
    ids_digest = hashlib.sha256("\n".join(sorted(p["id"] for p in posts)).encode()).hexdigest()
    return {
        "schema_version": "6.1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "subject": "Serenity (public posts)",
        "post_count": len(posts),
        "first_post": posts[0]["created_at"] if posts else None,
        "archive_through": posts[-1]["created_at"] if posts else None,
        "post_id_set_sha256": ids_digest,
        "posts_per_month": dict(sorted(months.items())),
        "extractor": EXTRACTOR_VERSION,
        "event_count": len(events),
        "action_counts": dict(sorted(actions.items())),
        "ticker_mentions_top": [{"ticker": t, "mentions": n, "in_atlas": t in atlas_tickers or t.split(".")[0] in atlas_tickers}
                                for t, n in mentions.most_common(80)],
        "note": ("Counts and IDs only. Post text lives in the maintainer's private archive and is never "
                 "committed to the public skill repo. The skill is a framework distilled from Serenity's "
                 "public posts for research/backtesting; it does not speak for Serenity."),
    }


def _atlas_tickers() -> set[str]:
    atlas = json.loads((ROOT / "assets" / "chokepoint-atlas.json").read_text(encoding="utf-8"))
    out: set[str] = set()
    for ch in atlas["chains"]:
        for node in ch["nodes"]:
            for h in node["holders"]:
                out.add(h["ticker"].upper())
                out.add(h["ticker"].upper().split(".")[0])
    return out


def cmd_refresh(args: argparse.Namespace) -> int:
    pdir = private_dir(args.private_dir)
    archive = Path(args.archive) if args.archive else pdir / "posts.jsonl"
    events_path = Path(args.events) if args.events else pdir / "events.jsonl"
    guard_private_path(archive)
    guard_private_path(events_path)
    posts = sorted(load_archive(archive).values(), key=lambda r: (r["created_at"], r["id"]))
    if not posts:
        raise SystemExit(f"no posts in {archive}")
    aliases = load_aliases([*(Path(a) for a in args.aliases), SEED_PATH])
    events: list[dict[str, Any]] = []
    for p in posts:
        events.extend(extract_post(p, aliases))
    write_jsonl(events_path, events)
    # The PUBLIC manifest describes public posts only: subscription posts stay in the private
    # archive (for the maintainer's own-words distillation) and never show up in public counts.
    public_posts = [p for p in posts if p.get("source_partition", p.get("access_level", "public")) == "public"]
    public_events = [e for e in events if e.get("source_partition", "public") == "public"]
    manifest = build_manifest(public_posts, public_events, _atlas_tickers())
    out = Path(args.manifest) if args.manifest else MANIFEST_PATH
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"posts": len(posts), "public_posts": len(public_posts), "events": len(events),
                      "public_events": len(public_events), "events_path": str(events_path),
                      "manifest": str(out), "archive_through": manifest["archive_through"]}, ensure_ascii=False))
    return 0


def cmd_gaps(args: argparse.Namespace) -> int:
    pdir = private_dir(args.private_dir)
    archive = Path(args.archive) if args.archive else pdir / "posts.jsonl"
    guard_private_path(archive)
    since = args.since or "0000"
    posts = [p for p in sorted(load_archive(archive).values(), key=lambda r: r["created_at"]) if p["created_at"] >= since]
    aliases = load_aliases([*(Path(a) for a in args.aliases), SEED_PATH])
    known = _atlas_tickers()
    untracked: dict[str, list[str]] = defaultdict(list)
    queue: dict[str, list[str]] = {k: [] for k in FAMILIES}
    for p in posts:
        for t in tickers_in(p["text"], aliases):
            if t.upper() not in known and t.upper().split(".")[0] not in known:
                untracked[t.upper()].append(p["id"])
        for fam, pat in FAMILIES.items():
            if re.search(pat, p["text"], re.I):
                queue[fam].append(p["id"])
    out = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "since": args.since, "posts_considered": len(posts),
        "untracked_tickers": sorted(({"ticker": t, "mentions": len(ids), "post_ids": ids[:8]} for t, ids in untracked.items()),
                                    key=lambda x: -x["mentions"])[:60],
        "review_queue": {k: v[-40:] for k, v in queue.items() if v},
        "how_to_use": ("Read each post in the private archive, then write OWN-WORDS rules/cards with post IDs in "
                       "references/serenity-doctrine.md / serenity-case-library.md and atlas nodes "
                       "(basis serenity_lead + post_ids). Never paste post text into the public repo."),
    }
    target = Path(args.out) if args.out else pdir / "review-queue.json"
    guard_private_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"review_queue": str(target), "posts_considered": len(posts),
                      "untracked_tickers": len(out["untracked_tickers"]),
                      "families": {k: len(v) for k, v in out["review_queue"].items()}}, ensure_ascii=False))
    return 0


WORD_RE = re.compile(r"[a-z0-9$]+|[\u4e00-\u9fff]", re.I)


def shingles(text: str, n: int) -> set[str]:
    words = [w.lower() for w in WORD_RE.findall(text)]
    return {hashlib.blake2b(" ".join(words[i:i + n]).encode(), digest_size=8).hexdigest()
            for i in range(0, max(0, len(words) - n + 1))}


def public_files(root: Path) -> list[Path]:
    try:
        res = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
                             capture_output=True, text=True, check=True)
        names = [n for n in res.stdout.splitlines() if n]
    except (OSError, subprocess.CalledProcessError):
        names = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    return [root / n for n in names if (root / n).suffix.lower() in TEXT_SUFFIXES and (root / n).is_file()]


def leak_scan(archive_posts: Iterable[dict[str, Any]], files: list[Path], n: int = 12) -> list[dict[str, Any]]:
    index: dict[str, str] = {}
    for p in archive_posts:
        for h in shingles(p["text"], n):
            index.setdefault(h, p["id"])
    hits = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        matched = {index[h] for h in shingles(text, n) if h in index}
        if matched:
            hits.append({"file": str(f), "posts": sorted(matched)[:10], "count": len(matched)})
    return hits


def cmd_check(args: argparse.Namespace) -> int:
    archive = Path(args.archive) if args.archive else private_dir(args.private_dir) / "posts.jsonl"
    if not archive.exists():
        print(f"SKIP: no private archive at {archive}; nothing to compare against (set SERENITY_PRIVATE_DIR).")
        return 0 if not args.strict else 1
    root = Path(args.root).resolve()
    hits = leak_scan(load_archive(archive).values(), public_files(root), args.ngram)
    if hits:
        for h in hits:
            print(f"LEAK: {h['file']} shares {args.ngram}-word runs with {h['count']} post(s), e.g. {', '.join(h['posts'][:3])}")
        print("Refusing: rewrite in your own words and keep only post IDs before pushing.")
        return 1
    print(f"OK: no {args.ngram}-word overlap between {root} public files and the private archive.")
    return 0


HOOK = """#!/bin/sh
# installed by scripts/serenity_update.py install-hook
python3 "$(git rev-parse --show-toplevel)/scripts/serenity_update.py" check || exit 1
"""


def cmd_install_hook(args: argparse.Namespace) -> int:
    hook = ROOT / ".git" / "hooks" / "pre-push"
    if not hook.parent.exists():
        raise SystemExit("not a git checkout")
    hook.write_text(HOOK, encoding="utf-8")
    hook.chmod(0o755)
    print(f"OK: pre-push leak guard installed at {hook}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--private-dir", help="default: $SERENITY_PRIVATE_DIR or ~/.serenity-private")
    common = argparse.ArgumentParser(add_help=False)  # also accept --private-dir after the subcommand
    common.add_argument("--private-dir", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ingest", parents=[common]); s.add_argument("inputs", nargs="+"); s.add_argument("--archive")
    s = sub.add_parser("refresh", parents=[common]); s.add_argument("--archive"); s.add_argument("--events"); s.add_argument("--manifest")
    s.add_argument("--aliases", action="append", default=[])
    s = sub.add_parser("gaps", parents=[common]); s.add_argument("--archive"); s.add_argument("--since"); s.add_argument("--out")
    s.add_argument("--aliases", action="append", default=[])
    s = sub.add_parser("check", parents=[common]); s.add_argument("--archive"); s.add_argument("--root", default=str(ROOT))
    s.add_argument("--ngram", type=int, default=12); s.add_argument("--strict", action="store_true", help="fail when no archive is configured")
    sub.add_parser("install-hook", parents=[common])
    args = ap.parse_args(argv)
    return {"ingest": cmd_ingest, "refresh": cmd_refresh, "gaps": cmd_gaps, "check": cmd_check,
            "install-hook": cmd_install_hook}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
