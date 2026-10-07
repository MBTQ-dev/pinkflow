"""
PinkFlow Deterministic Audit Pipeline
Module 2: deafauth_classifier.py

Classifies DeafAuth integration presence and correctness across the repo.
Detects: PASETO usage, JWT anti-patterns, auth endpoint references,
DeafAuth SDK imports, token validation patterns.

Deterministic: pure input→output, no network, no randomness.
"""

from __future__ import annotations

import re
from typing import Any

SCHEMA_VERSION = "pinkflow.audit.v1"

# ── Detection patterns ───────────────────────────────────────────────────────

PASETO_PATTERNS = [
    r"paseto",
    r"v4\.local",
    r"v4\.public",
    r"PasetoToken",
    r"deafauth.*paseto",
    r"paseto.*deafauth",
]

JWT_ANTIPATTERN = [
    r"jwt\.sign\(",
    r"jsonwebtoken",
    r"verify.*jwt",
    r"jwt\.verify\(",
    r"Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
]

DEAFAUTH_SDK_PATTERNS = [
    r"@mbtq/auth-client",
    r"deafauth",
    r"DeafAuth",
    r"authenticateWithDeafAuth",
    r"deafauth\.mbtq\.dev",
    r"auth\.pinkflow\.io",
]

AUTH_ENDPOINT_PATTERNS = [
    r"https?://deafauth",
    r"https?://auth\.mbtq\.dev",
    r"https?://auth\.pinkflow\.io",
    r"/api/auth",
    r"/v1/auth",
]

PASETO_COMPILED = [re.compile(p, re.IGNORECASE) for p in PASETO_PATTERNS]
JWT_COMPILED = [re.compile(p, re.IGNORECASE) for p in JWT_ANTIPATTERN]
SDK_COMPILED = [re.compile(p, re.IGNORECASE) for p in DEAFAUTH_SDK_PATTERNS]
ENDPOINT_COMPILED = [re.compile(p, re.IGNORECASE) for p in AUTH_ENDPOINT_PATTERNS]


def _matches_any(content: str, patterns: list[re.Pattern]) -> list[str]:
    return sorted({p.pattern for p in patterns if p.search(content)})


def classify_file(file_entry: dict[str, Any], content: str) -> dict[str, Any]:
    """Classify DeafAuth signals in a single file."""
    return {
        "auth_endpoints": _matches_any(content, ENDPOINT_COMPILED),
        "deafauth_sdk": _matches_any(content, SDK_COMPILED),
        "jwt_antipatterns": _matches_any(content, JWT_COMPILED),
        "paseto_usage": _matches_any(content, PASETO_COMPILED),
        "path": file_entry["path"],
    }


def classify_deafauth(
    normalized: dict[str, Any],
    file_contents: dict[str, str],
) -> dict[str, Any]:
    """
    Run DeafAuth classification across all normalized files.

    Args:
        normalized: Output from normalizer.normalize_inputs()
        file_contents: Dict of {relative_path: file_content_string}

    Returns:
        Sorted, deterministic classification result.
    """
    results: list[dict[str, Any]] = []
    jwt_violations: list[str] = []
    paseto_files: list[str] = []
    sdk_files: list[str] = []

    for file_entry in normalized["files"]:
        path = file_entry["path"]
        content = file_contents.get(path, "")
        classified = classify_file(file_entry, content)

        if classified["jwt_antipatterns"]:
            jwt_violations.append(path)
        if classified["paseto_usage"]:
            paseto_files.append(path)
        if classified["deafauth_sdk"]:
            sdk_files.append(path)

        # Only include files with at least one signal
        has_signal = any([
            classified["paseto_usage"],
            classified["jwt_antipatterns"],
            classified["deafauth_sdk"],
            classified["auth_endpoints"],
        ])
        if has_signal:
            results.append(classified)

    results.sort(key=lambda r: r["path"])

    compliance_status = "PASS"
    if jwt_violations:
        compliance_status = "FAIL"
    elif not paseto_files and not sdk_files:
        compliance_status = "WARN"

    return {
        "compliance_status": compliance_status,
        "files_with_signals": results,
        "jwt_violation_paths": sorted(jwt_violations),
        "paseto_file_paths": sorted(paseto_files),
        "schema_version": SCHEMA_VERSION,
        "sdk_file_paths": sorted(sdk_files),
        "summary": {
            "jwt_violations": len(jwt_violations),
            "paseto_usages": len(paseto_files),
            "sdk_usages": len(sdk_files),
        },
    }


# ── Unit test stubs ──────────────────────────────────────────────────────────

def _test_paseto_detected() -> None:
    entry = {"path": "src/auth.ts"}
    content = "import { PasetoToken } from '@mbtq/auth-client';"
    result = classify_file(entry, content)
    assert result["paseto_usage"]
    assert result["deafauth_sdk"]
    print("PASS: paseto_detected")


def _test_jwt_violation() -> None:
    entry = {"path": "src/legacy.ts"}
    content = "const token = jwt.sign(payload, secret);"
    result = classify_file(entry, content)
    assert result["jwt_antipatterns"]
    print("PASS: jwt_violation")


def _test_clean_file() -> None:
    entry = {"path": "src/utils.ts"}
    content = "export const add = (a: number, b: number) => a + b;"
    result = classify_file(entry, content)
    assert not result["jwt_antipatterns"]
    assert not result["paseto_usage"]
    print("PASS: clean_file")


if __name__ == "__main__":
    _test_paseto_detected()
    _test_jwt_violation()
    _test_clean_file()
    print("All deafauth_classifier tests passed.")