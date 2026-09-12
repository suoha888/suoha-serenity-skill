#!/usr/bin/env python3
"""Shared helpers for building and verifying the public runtime artifact.

This module is intentionally dependency-free and network-free.  The runtime
allow-list is the boundary between the editable source repository and the
generated Agent Skill deployment directory.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RUNTIME_SCHEMA_VERSION = "3"
SKILL_VERSION = "3.0.0"
RUNTIME_MANIFEST_NAME = "BUILD-MANIFEST.json"

# Documentation and fixtures are public-safe source artifacts.  Historical raw
# archives, derived records, local indexes, and private overlays are never in
# this list.
RUNTIME_FILES = (
    "SKILL.md",
    "LICENSE",
    "agents/openai.yaml",
)
RUNTIME_DIRECTORIES = (
    "adapters",
    "assets",
    "contracts",
    "evals",
    "examples",
    "kernel",
    "references",
    "schemas",
    "scripts",
)
SKIP_DIRECTORY_NAMES = {".git", "__pycache__", ".mypy_cache", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_tree_hash(root: Path, relative_paths: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(relative_paths):
        path = root / relative
        digest.update(relative.replace("\\", "/").encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def runtime_file_paths(source_root: Path) -> list[Path]:
    """Return the exact public-safe files that belong in a runtime build."""
    source_root = source_root.resolve()
    paths: list[Path] = []
    for relative in RUNTIME_FILES:
        path = source_root / relative
        if path.is_file() and not path.is_symlink():
            paths.append(path)
    for directory in RUNTIME_DIRECTORIES:
        base = source_root / directory
        if not base.is_dir() or base.is_symlink():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            relative_parts = path.relative_to(source_root).parts
            if any(part in SKIP_DIRECTORY_NAMES for part in relative_parts):
                continue
            if path.suffix.lower() in SKIP_SUFFIXES:
                continue
            paths.append(path)
    return sorted(set(paths), key=lambda item: item.relative_to(source_root).as_posix())


def relative_runtime_paths(source_root: Path) -> list[str]:
    return [path.relative_to(source_root).as_posix() for path in runtime_file_paths(source_root)]


def file_manifest(root: Path, relative_paths: Iterable[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for relative in sorted(relative_paths):
        path = root / relative
        if not path.is_file() or path.is_symlink():
            continue
        result[relative] = {
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
    return result


def git_metadata(source_root: Path) -> dict[str, Any]:
    """Read only local git metadata; never fetches or contacts a remote."""
    result: dict[str, Any] = {
        "source_commit": None,
        "source_dirty": None,
        "git_available": False,
    }
    try:
        commit = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        status = subprocess.run(
            ["git", "-C", str(source_root), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return result
    result.update(
        {
            "source_commit": commit.stdout.strip() or None,
            "source_dirty": bool(status.stdout.strip()),
            "git_available": True,
        }
    )
    return result


def parse_frontmatter_name(skill_path: Path) -> str | None:
    text = skill_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    closing = text.find("\n---", 4)
    if closing < 0:
        return None
    for line in text[4:closing].splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return None


def build_manifest(source_root: Path, built_at: str | None = None) -> dict[str, Any]:
    source_root = source_root.resolve()
    relative_paths = relative_runtime_paths(source_root)
    metadata = git_metadata(source_root)
    return {
        "manifest_version": RUNTIME_SCHEMA_VERSION,
        "skill_name": parse_frontmatter_name(source_root / "SKILL.md"),
        "skill_version": SKILL_VERSION,
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "built_at": built_at or utc_now_iso(),
        "source_commit": metadata["source_commit"],
        "source_dirty": metadata["source_dirty"],
        "git_available": metadata["git_available"],
        "source_tree_sha256": stable_tree_hash(source_root, relative_paths),
        "files": file_manifest(source_root, relative_paths),
    }


def safe_resolve_child(base: Path, candidate: Path) -> Path:
    base = base.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"path escapes base directory: {candidate}") from exc
    return resolved
