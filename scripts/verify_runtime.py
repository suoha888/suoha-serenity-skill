#!/usr/bin/env python3
"""Verify that a runtime exactly matches the public source allow-list."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runtime_common import (
    RUNTIME_MANIFEST_NAME,
    build_manifest,
    file_manifest,
    parse_frontmatter_name,
    relative_runtime_paths,
    sha256_file,
)


def verify_runtime(source_root: Path, runtime_root: Path) -> dict:
    source_root = source_root.resolve()
    runtime_root = runtime_root.resolve()
    errors: list[str] = []
    manifest_path = runtime_root / RUNTIME_MANIFEST_NAME
    manifest: dict = {}
    if not runtime_root.is_dir():
        errors.append(f"runtime_missing:{runtime_root}")
    if not manifest_path.is_file():
        errors.append("build_manifest_missing")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"build_manifest_invalid:{exc}")

    expected = build_manifest(source_root, built_at=manifest.get("built_at") if manifest else None)
    expected_files = expected["files"]
    actual_files = file_manifest(runtime_root, relative_runtime_paths(source_root))
    missing = sorted(set(expected_files) - set(actual_files))
    mismatched = sorted(
        relative
        for relative in set(expected_files) & set(actual_files)
        if expected_files[relative] != actual_files[relative]
    )
    if missing:
        errors.extend(f"runtime_file_missing:{item}" for item in missing)
    if mismatched:
        errors.extend(f"runtime_file_mismatch:{item}" for item in mismatched)

    if runtime_root.is_dir():
        allowed = set(expected_files) | {RUNTIME_MANIFEST_NAME}
        for path in runtime_root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(runtime_root).as_posix()
            if relative not in allowed:
                errors.append(f"runtime_unmanaged_file:{relative}")

    expected_name = parse_frontmatter_name(source_root / "SKILL.md")
    actual_name = parse_frontmatter_name(runtime_root / "SKILL.md") if (runtime_root / "SKILL.md").is_file() else None
    if expected_name != actual_name:
        errors.append(f"runtime_skill_name_mismatch:{expected_name!r}!={actual_name!r}")
    if runtime_root.name != expected_name:
        errors.append(f"runtime_directory_name_mismatch:{runtime_root.name!r}!={expected_name!r}")
    if manifest:
        if manifest.get("skill_name") != expected_name:
            errors.append("build_manifest_skill_name_mismatch")
        if manifest.get("source_tree_sha256") != expected["source_tree_sha256"]:
            errors.append("build_manifest_source_tree_mismatch")
        if manifest.get("files") != expected_files:
            errors.append("build_manifest_file_manifest_mismatch")

    return {
        "status": "pass" if not errors else "fail",
        "source": str(source_root),
        "runtime": str(runtime_root),
        "expected_file_count": len(expected_files),
        "actual_file_count": len(actual_files),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--json", action="store_true", help="emit the full JSON report")
    args = parser.parse_args()
    try:
        report = verify_runtime(args.source, args.runtime)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{report['status'].upper()}: runtime verification ({report['actual_file_count']} files)")
        for error in report["errors"]:
            print(f"- {error}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
