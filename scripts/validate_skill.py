#!/usr/bin/env python3
"""Validate the structure and public boundary of an Agent Skill."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


SKILL_NAME_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
MAX_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1024
REQUIRED_FILES = (
    "SKILL.md",
    "docs/ARCHITECTURE.md",
    "LICENSE",
    "agents/openai.yaml",
    "README.md",
    "docs/CHANGELOG.md",
    ".github/CONTRIBUTING.md",
    ".github/SECURITY.md",
    "docs/DATA_POLICY.md",
    "docs/THIRD_PARTY_NOTICES.md",
    "kernel/RESEARCH_KERNEL.md",
    "contracts/output-contract.md",
    "contracts/provenance-contract.md",
    "contracts/temporal-contract.md",
    "contracts/access-control-contract.md",
    "contracts/company-research-contract.md",
    "references/company-research-and-valuation.md",
    "references/advanced-bottleneck-diagnostics.md",
    "schemas/claim.schema.json",
    "schemas/evidence.schema.json",
    "schemas/thesis.schema.json",
    "schemas/thesis-event.schema.json",
    "schemas/method-card.schema.json",
    "schemas/context-pack.schema.json",
    "schemas/manifest.schema.json",
    "schemas/bottleneck-assessment.schema.json",
    "schemas/company-profile.schema.json",
    "schemas/market-snapshot.schema.json",
    "schemas/valuation-snapshot.schema.json",
    "schemas/research-output.schema.json",
    "scripts/build_runtime.py",
    "scripts/verify_runtime.py",
    "scripts/distill_archive.py",
    "scripts/build_local_index.py",
    "scripts/run_evals.py",
    "scripts/validate_research_output.py",
    "scripts/validate_research_bundle.py",
    "scripts/method_catalog.py",
    "evals/company-research.jsonl",
    "evals/fixtures/research-output.synthetic.json",
    "evals/fixtures/company-research-components.synthetic.json",
    "evals/rubrics/company-research.md",
    "references/serenity-playbook.md",
    "references/serenity-exceptions.md",
    "scripts/serenity_timeline.py",
    "assets/serenity-public-timeline.json",
    "references/company-type-routing.md",
    "references/supply-chain-taxonomy.md",
    "schemas/serenity-lens.schema.json",
    "schemas/stance-event.schema.json",
    "scripts/serenity_lens.py",
    "scripts/render_report.py",
    "scripts/verify_report.py",
    "scripts/ticker_normalizer.py",
    "scripts/stance_ledger.py",
    "scripts/forward_returns.py",
    "scripts/eval_alignment.py",
    "assets/ticker-aliases.seed.json",
    "assets/stance-extraction-prompt.md",
    "assets/serenity-report-template.md",
    "examples/amd-serenity-lens.json",
    "references/serenity-doctrine.md",
    "references/serenity-case-library.md",
    "references/chokepoint-atlas.md",
    "assets/chokepoint-atlas.json",
    "scripts/atlas.py",
    "scripts/chokepoint_scan.py",
    "connectors/live_data.py",
    "examples/axti-serenity-lens.json",
    "examples/live/axti-snapshot-2026-10-18.json",
)
FORBIDDEN_FILE_MARKERS = (
    "Raw_Data",
    "raw_archive",
    "subscription_dump",
    "private_archive",
)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Read the flat ``key: value`` header between the two ``---`` fences."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("frontmatter: first line of SKILL.md must be '---'")
    try:
        close = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        raise ValueError("frontmatter: no closing '---' line found in SKILL.md") from None
    fields: dict[str, str] = {}
    for line in lines[1:close]:
        # This deliberately small parser is not a YAML implementation. Reject
        # ambiguous plain scalars that YAML clients interpret as mappings.
        if ":" in line:
            scalar = line.partition(":")[2].strip()
            if ": " in scalar and not scalar.startswith(('"', "'", "|", ">")):
                raise ValueError("frontmatter: quote scalar values containing ': '")
        if not line or line[0] in " \t" or ":" not in line:
            continue  # nested or continuation lines are not needed here
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip("\"'")
    return fields


def validate(root: Path, strict: bool = False, any_folder: bool = False) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    skill_path = root / "SKILL.md"
    if not skill_path.is_file():
        return [f"missing {skill_path}"]
    try:
        frontmatter = parse_frontmatter(skill_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [str(exc)]
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if not SKILL_NAME_PATTERN.fullmatch(name):
        errors.append(f"frontmatter name {name!r}: only a-z, 0-9 and single hyphens allowed")
    if len(name) > MAX_NAME_LEN:
        errors.append(f"frontmatter name longer than {MAX_NAME_LEN} chars")
    if root.name != name and not any_folder:  # installers: a ZIP download unpacks to <name>-main
        errors.append(f"folder {root.name!r} differs from frontmatter name {name!r}")
    if not description:
        errors.append("frontmatter description is empty")
    elif len(description) > MAX_DESCRIPTION_LEN:
        errors.append(f"frontmatter description is {len(description)} chars (limit {MAX_DESCRIPTION_LEN})")
    if frontmatter.get("license") != "MIT":
        errors.append("license must be MIT for this public build")

    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing {relative}")

    body = skill_path.read_text(encoding="utf-8")
    required_terms = (
        "research_cutoff",
        "UNKNOWN",
        "provenance",
        "subscription",
        "untrusted",
        "falsifiable",
        "build_runtime.py",
        "verify_runtime.py",
        "BottleneckAssessment",
        "CompanyProfile",
        "MarketSnapshot",
        "conditional",
        "single composite",
        "architecture_necessity",
        "validation ladder",
        "reflexivity",
        "live_data",
        "serenity-doctrine.md",
        "chokepoint_scan.py",
        "atlas.py",
        "variant_perception",
    )
    for term in required_terms:
        if term.lower() not in body.lower():
            errors.append(f"SKILL.md missing integration term: {term}")

    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        if any(marker.lower() in relative.lower() for marker in FORBIDDEN_FILE_MARKERS):
            errors.append(f"forbidden archive-like filename: {relative}")
        if strict and path.stat().st_size > 5 * 1024 * 1024:
            errors.append(f"strict public skill file is unexpectedly large: {relative}")

    openai_yaml = root / "agents" / "openai.yaml"
    if openai_yaml.is_file():
        yaml_text = openai_yaml.read_text(encoding="utf-8")
        if "display_name: \"suoha-serenity skill\"" not in yaml_text:
            errors.append("agents/openai.yaml must expose the requested display name")
        if "allow_implicit_invocation: true" not in yaml_text:
            errors.append("implicit invocation must remain enabled")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--any-folder", action="store_true",
                        help="skip the folder-name check (source checkouts such as a ZIP download named <name>-main)")
    args = parser.parse_args()
    errors = validate(args.root, strict=args.strict, any_folder=args.any_folder)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAILED: {len(errors)} skill checks")
        return 1
    print(f"OK: {args.root.resolve().name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
