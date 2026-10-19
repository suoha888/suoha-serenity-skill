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
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runtime_common import (
    RUNTIME_MANIFEST_NAME,
    RUNTIME_SCHEMA_VERSION,
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


def _validate_replace_target(output: Path, expected_name: str) -> None:
    """Only replace a runtime whose manifest still matches every file."""
    if output.is_symlink() or not output.is_dir():
        raise ValueError(f"refusing to replace a non-directory or linked runtime: {output}")
    manifest_path = output / RUNTIME_MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError(f"refusing to replace an unmanaged runtime (manifest missing): {output}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"refusing to replace an invalid runtime manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError(f"refusing to replace an unrecognized runtime: {output}")
    files = manifest.get("files")
    if (
        manifest.get("skill_name") != expected_name
        or manifest.get("manifest_version") != RUNTIME_SCHEMA_VERSION
        or not isinstance(files, dict)
        or not files
        or any(not isinstance(relative, str) for relative in files)
        or manifest.get("output_file_count") != len(files)
    ):
        raise ValueError(f"refusing to replace an unrecognized runtime: {output}")

    expected_paths = set(files) | {RUNTIME_MANIFEST_NAME}
    actual_paths: set[str] = set()
    for path in output.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"refusing to replace a runtime containing a symlink: {path}")
        if path.is_file():
            actual_paths.add(path.relative_to(output).as_posix())
    if actual_paths != expected_paths:
        unexpected = sorted(actual_paths - expected_paths)
        missing = sorted(expected_paths - actual_paths)
        raise ValueError(
            "refusing to replace a runtime whose file set differs from its manifest; "
            f"unexpected={unexpected}, missing={missing}"
        )
    for relative in files:
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"runtime manifest contains an unsafe path: {relative}")
    if file_manifest(output, files) != files:
        raise ValueError(f"refusing to replace a runtime with modified files: {output}")


def _backup_path(output: Path) -> Path:
    backup_base = output.parent / ".runtime-backups"
    if backup_base.is_symlink():
        raise ValueError("runtime backup directory cannot be a symlink")
    backup_root = backup_base / output.name
    if backup_root.is_symlink():
        raise ValueError("skill runtime backup directory cannot be a symlink")
    backup_root.mkdir(parents=True, exist_ok=True)
    try:
        backup_root.resolve().relative_to(output.parent.resolve())
    except ValueError as exc:
        raise ValueError("runtime backup path escapes the output parent") from exc
    stamp = utc_now_iso().replace(":", "").replace("-", "")
    return backup_root / f"{stamp}-{uuid.uuid4().hex[:8]}"


def build_runtime(
    source_root: Path,
    output: Path,
    *,
    replace: bool = False,
    require_clean: bool = False,
) -> dict:
    source_root = source_root.resolve()
    if output.is_symlink():
        raise ValueError("runtime output cannot be a symlink")
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
    if output.exists():
        _validate_replace_target(output, expected_name)

    built_at = utc_now_iso()
    manifest = build_manifest(source_root, built_at=built_at)
    if require_clean and (
        manifest.get("git_available") is not True
        or manifest.get("source_dirty") is not False
    ):
        raise ValueError(
            "release build requires a clean, Git-tracked source tree; "
            f"git_available={manifest.get('git_available')}, "
            f"source_dirty={manifest.get('source_dirty')}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.build-", dir=str(output.parent)))
    backup: Path | None = None
    try:
        copied = _copy_runtime_tree(source_root, staging)
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
            backup = _backup_path(output)
            output.rename(backup)
            manifest["replacement_backup"] = backup.as_posix()
            (staging / RUNTIME_MANIFEST_NAME).write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        try:
            staging.replace(output)
        except Exception:
            if backup is not None and backup.exists() and not output.exists():
                backup.replace(output)
            raise
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
        help="replace only a verified generated runtime, keeping the previous one recoverable",
    )
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="refuse release builds unless the Git source tree is clean and tracked",
    )
    args = parser.parse_args()
    try:
        manifest = build_runtime(
            args.source,
            args.output,
            replace=args.replace,
            require_clean=args.require_clean,
        )
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
