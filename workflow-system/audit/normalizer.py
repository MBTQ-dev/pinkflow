"""
PinkFlow Deterministic Audit Pipeline
Module 1: normalizer.py

Normalizes all raw inputs into a stable, sorted, schema-versioned dict.
Deterministic: same input always produces same output.
No network calls. No randomness. No time-dependent values.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "pinkflow.audit.v1"

SUPPORTED_EXTENSIONS = {
    ".py", ".ts", ".js", ".tsx", ".jsx",
    ".json", ".yaml", ".yml", ".toml",
    ".md", ".mdx", ".env.example",
    ".dockerfile", ".sh",
}


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _normalize_path(p: str) -> str:
    """Return POSIX path with forward slashes, stripped of leading ./"""
    return Path(p).as_posix().lstrip("./")


def normalize_file_entry(path: str, content: str) -> dict[str, Any]:
    """Produce a stable, sorted dict for a single file."""
    return {
        "content_sha256": _sha256(content),
        "extension": Path(path).suffix.lower(),
        "lines": content.count("\n") + 1,
        "path": _normalize_path(path),
        "size_bytes": len(content.encode("utf-8")),
    }


def normalize_inputs(
    root_path: str,
    schema_version: str = SCHEMA_VERSION,
) -> dict[str, Any]:
    """
    Walk root_path, collect supported files, return normalized manifest.

    Args:
        root_path: Absolute or relative path to repo root.
        schema_version: Schema version string for output.

    Returns:
        Stable, sorted, deterministic manifest dict.
    """
    root = Path(root_path).resolve()
    files: list[dict[str, Any]] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Stable traversal — sort in place to ensure determinism
        dirnames.sort()
        for filename in sorted(filenames):
            ext = Path(filename).suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            full_path = Path(dirpath) / filename
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel_path = full_path.relative_to(root).as_posix()
            files.append(normalize_file_entry(rel_path, content))

    # Sort by path for determinism
    files.sort(key=lambda f: f["path"])

    return {
        "files": files,
        "root": root.as_posix(),
        "schema_version": schema_version,
        "total_files": len(files),
        "total_lines": sum(f["lines"] for f in files),
        "total_size_bytes": sum(f["size_bytes"] for f in files),
    }


# ── Unit test stubs ──────────────────────────────────────────────────────────

def _test_normalize_file_entry() -> None:
    result = normalize_file_entry("src/index.ts", "const x = 1;\n")
    assert result["path"] == "src/index.ts"
    assert result["lines"] == 2
    assert isinstance(result["content_sha256"], str)
    assert len(result["content_sha256"]) == 64
    print("PASS: normalize_file_entry")


def _test_normalize_inputs_empty(tmp_path: Any) -> None:
    result = normalize_inputs(str(tmp_path))
    assert result["total_files"] == 0
    assert result["files"] == []
    assert result["schema_version"] == SCHEMA_VERSION
    print("PASS: normalize_inputs_empty")


if __name__ == "__main__":
    _test_normalize_file_entry()
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as d:
        _test_normalize_inputs_empty(pathlib.Path(d))
    print("All normalizer tests passed.")