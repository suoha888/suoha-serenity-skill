#!/usr/bin/env python3
"""Build a deterministic, public-safe Agent Skill runtime.

The source repository is editable.  A runtime is a generated artifact and is
never hand-maintained.  The command refuses ambiguous paths and copies only the
allow-listed skill resources from runtime_common.py.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runtime_common import (
    RUNTIME_MANIFEST_NAME,
    RUNTIME_FILES,
    build_manifest,
    file_manifest,
    relative_runtime_paths,
    parse_frontmatter_name,
    safe_resolve_child,
    stable_tree_hash,
    utc_now_iso,
    runtime_file_paths,
)


def _copy_runtime_tree(source_root: Path, destination: Path) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for source_path in runtime_file_paths(source_root):
        relative = source_path.relative_to(source_root).as_posix()
        target = safe_resolve_child(destination, destination / relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)
        copied.append(relative)
    return copied


def build_runtime(source_root: Path, output: Path, *, replace: bool = False) -> dict:
    source_root = source_root.resolve()
    output = output.resolve()
    if not source_root.is_dir():
        raise ValueError(f"source root does not exist: {source_root}")
    if not (source_root / "SKILL.md").is_file():
        raise ValueError("source root must contain SKILL.md")
    expected_name = parse_frontmatter_name(source_root / "SKILL.md")
    if not expected_name:
        raise ValueError("SKILL.md must declare a machine-readable name")
    if output.name != expected_name:
        raise ValueError(
            f"runtime output directory must be named {expected_name!r}; got {output.name!r}"
        )
    for relative in RUNTIME_FILES:
        if not (source_root / relative).is_file():
            raise ValueError(f"required runtime file missing: {relative}")
    if output == source_root or source_root in output.parents:
        raise ValueError("runtime output cannot be the source directory or inside it")
    if output.exists() and not replace:
        raise FileExistsError(f"output exists; pass --replace to regenerate: {output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.build-", dir=str(output.parent)))
    try:
        copied = _copy_runtime_tree(source_root, staging)
        built_at = utc_now_iso()
        manifest = build_manifest(source_root, built_at=built_at)
        manifest["output_file_count"] = len(copied)
        manifest["public_safe_allowlist"] = {
            "files": list(RUNTIME_FILES),
            "directories": [
                path for path in sorted(
                    {relative.split("/", 1)[0] for relative in copied if "/" in relative}
                )
            ],
        }
        (staging / RUNTIME_MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if output.exists():
            shutil.rmtree(output)
        staging.replace(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace an existing generated runtime after staging succeeds",
    )
    args = parser.parse_args()
    try:
        manifest = build_runtime(args.source, args.output, replace=args.replace)
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        f"OK: built {manifest['skill_name']} "
        f"({manifest['output_file_count']} files) -> {args.output.resolve()}"
    )
    print(f"source_tree_sha256: {manifest['source_tree_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
