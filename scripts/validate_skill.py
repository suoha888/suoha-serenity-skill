#!/usr/bin/env python3
"""Validate the structure and public boundary of an Agent Skill."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REQUIRED_FILES = (
    "SKILL.md",
    "ARCHITECTURE_V4.md",
    "LICENSE",
    "agents/openai.yaml",
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "DATA_POLICY.md",
    "THIRD_PARTY_NOTICES.md",
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
    "evals/company-research.jsonl",
    "evals/fixtures/research-output.synthetic.json",
    "evals/fixtures/company-research-components.synthetic.json",
    "evals/rubrics/company-research.md",
)
FORBIDDEN_FILE_MARKERS = (
    "Raw_Data",
    "raw_archive",
    "subscription_dump",
    "private_archive",
)


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter closing delimiter missing")
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line[:1].isspace():
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def validate(root: Path, strict: bool = False) -> list[str]:
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
    if not NAME_RE.fullmatch(name):
        errors.append("name must use lowercase letters, numbers, and hyphens")
    if len(name) > 64:
        errors.append("name exceeds 64 characters")
    if root.name != name:
        errors.append(f"parent directory name {root.name!r} must match name {name!r}")
    if not description:
        errors.append("description is required")
    if len(description) > 1024:
        errors.append(f"description exceeds 1024 characters: {len(description)}")
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
    args = parser.parse_args()
    errors = validate(args.root, strict=args.strict)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAILED: {len(errors)} skill checks")
        return 1
    print(f"OK: {args.root.resolve().name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
