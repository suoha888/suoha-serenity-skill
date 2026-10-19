#!/usr/bin/env python3
"""Delivery contract for rendered Serenity reports (v5 + v6 sections). Run before handing a
report to anyone.

Checks: all required sections present; embedded lens JSON matches its SHA-256
(no hand edits after rendering); the embedded lens still passes
serenity_lens.validate; the visible market cap and scenario per-share values
match the lens; disclaimer present.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_report import FRAMEWORK_NOTICE, REQUIRED_SECTIONS, canonical, fmt_money, required_sections  # noqa: E402
from serenity_lens import validate  # noqa: E402


def verify_markdown(text: str, lens_path: Path | None) -> list[str]:
    """Markdown reports carry section markers and the lens hash; the lens JSON
    itself lives next to the report and must be supplied with --lens."""
    errors = [f"report:missing_section:{sec}" for sec in REQUIRED_SECTIONS if f"<!-- section:{sec} -->" not in text]
    if lens_path is not None and lens_path.exists():
        peek = json.loads(lens_path.read_text(encoding="utf-8"))
        errors += [f"report:missing_section:{sec}" for sec in required_sections(peek)[len(REQUIRED_SECTIONS):]
                   if f"<!-- section:{sec} -->" not in text]
    m = re.search(r"<!-- serenity-lens lens_id=(\S+) sha256=([0-9a-f]{64}) -->", text)
    if not m:
        return errors + ["report:missing_lens_hash_marker"]
    if lens_path is None:
        return errors + ["report:markdown_requires_--lens"]
    lens = json.loads(lens_path.read_text(encoding="utf-8"))
    if lens.get("lens_id") != m.group(1):
        errors.append("report:lens_id_mismatch")
    if hashlib.sha256(canonical(lens).encode("utf-8")).hexdigest() != m.group(2):
        errors.append("report:lens_hash_mismatch_render_again")
    errors += [f"report:{x}" for x in validate(lens)]
    cur = lens["valuation"]["current"]
    if fmt_money(cur["market_cap"], cur["currency"]) not in text:
        errors.append("report:visible_market_cap_differs_from_lens")
    for sc in lens["valuation"]["scenarios"]:
        if f"| {sc['implied_per_share']:.2f} |" not in text:
            errors.append(f"report:visible_scenario_differs_from_lens:{sc['name']}")
    if "非投资建议" not in text and "not investment advice" not in text.lower() and "不构成投资建议" not in text:
        errors.append("report:disclaimer_missing")
    if FRAMEWORK_NOTICE not in text:
        errors.append("report:framework_notice_missing")
    return errors


def verify(text: str) -> list[str]:
    errors: list[str] = []
    for sec in REQUIRED_SECTIONS:
        if f"id='{sec}'" not in text and f'id="{sec}"' not in text:
            errors.append(f"report:missing_section:{sec}")
    m = re.search(r"<script type='application/json' id='lens-data' data-sha256='([0-9a-f]{64})'>(.*?)</script>", text, re.S)
    if not m:
        return errors + ["report:missing_embedded_lens"]
    raw = html.unescape(m.group(2))
    try:
        lens = json.loads(raw)
    except json.JSONDecodeError:
        return errors + ["report:embedded_lens_not_json"]
    for sec in required_sections(lens)[len(REQUIRED_SECTIONS):]:
        if f"id='{sec}'" not in text and f'id="{sec}"' not in text:
            errors.append(f"report:missing_section:{sec}")
    digest = hashlib.sha256(canonical(lens).encode("utf-8")).hexdigest()
    if digest != m.group(1):
        errors.append("report:embedded_lens_hash_mismatch")
    errors += [f"report:{x}" for x in validate(lens)]
    body = text[: m.start()]
    cur = lens["valuation"]["current"]
    if html.escape(fmt_money(cur["market_cap"], cur["currency"])) not in body:
        errors.append("report:visible_market_cap_differs_from_lens")
    for sc in lens["valuation"]["scenarios"]:
        if f"<td>{sc['implied_per_share']:.2f}</td>" not in body:
            errors.append(f"report:visible_scenario_differs_from_lens:{sc['name']}")
    if "非投资建议" not in body and "not investment advice" not in body.lower() and "不构成投资建议" not in body:
        errors.append("report:disclaimer_missing")
    if html.escape(FRAMEWORK_NOTICE) not in body:
        errors.append("report:framework_notice_missing")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("report", type=Path, help="rendered .html (self-contained) or .md report")
    ap.add_argument("--lens", type=Path, help="lens JSON (required for .md reports)")
    args = ap.parse_args(argv)
    text = args.report.read_text(encoding="utf-8")
    errors = verify_markdown(text, args.lens) if args.report.suffix.lower() == ".md" else verify(text)
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1
    print(f"OK: {args.report} satisfies the delivery contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
