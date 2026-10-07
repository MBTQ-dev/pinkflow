"""
PinkFlow Deterministic Audit Pipeline
Module 3: accessibility_nodes.py

Detects accessibility (a11y) signals across the repo:
- ARIA attributes
- ASL / sign language references
- Visual-first patterns
- Caption / transcript handling
- Deaf-First design markers
- WCAG compliance indicators

Deterministic: pure input→output, no network, no randomness.
"""

from __future__ import annotations

import re
from typing import Any

SCHEMA_VERSION = "pinkflow.audit.v1"

# ── Detection patterns ───────────────────────────────────────────────────────

ARIA_PATTERNS = [
    r"aria-label",
    r"aria-describedby",
    r"aria-live",
    r"aria-hidden",
    r"role=\"",
    r"aria-expanded",
    r"aria-controls",
]

ASL_PATTERNS = [
    r"\bASL\b",
    r"sign.?language",
    r"SignMirror",
    r"asl.?gloss",
    r"gesture.?map",
    r"sign.?video",
    r"deaf.?first",
    r"DeafFirst",
    r"@mbtq/a11y",
    r"a11y\.mbtq\.dev",
]

CAPTION_PATTERNS = [
    r"caption",
    r"transcript",
    r"subtitle",
    r"WebVTT",
    r"\.vtt",
    r"whisper",
    r"closed.?caption",
    r"live.?caption",
]

VISUAL_FIRST_PATTERNS = [
    r"visual.?first",
    r"high.?contrast",
    r"focus.?visible",
    r":focus-visible",
    r"prefers.?reduced.?motion",
    r"color.?blind",
    r"wcag",
    r"WCAG",
]

WCAG_PATTERNS = [
    r"WCAG\s*2\.[01]",
    r"WCAG\s*3",
    r"AA\s+complian",
    r"AAA\s+complian",
    r"accessibility.*standard",
]

ANTI_A11Y_PATTERNS = [
    r"<blink",
    r"<marquee",
    r"onmouseover=",
    r"color\s*:\s*red.*!important",   # common a11y mistake
    r"display\s*:\s*none.*aria",       # hidden but aria-referenced
]

ARIA_C = [re.compile(p, re.IGNORECASE) for p in ARIA_PATTERNS]
ASL_C = [re.compile(p, re.IGNORECASE) for p in ASL_PATTERNS]
CAPTION_C = [re.compile(p, re.IGNORECASE) for p in CAPTION_PATTERNS]
VISUAL_C = [re.compile(p, re.IGNORECASE) for p in VISUAL_FIRST_PATTERNS]
WCAG_C = [re.compile(p, re.IGNORECASE) for p in WCAG_PATTERNS]
ANTI_C = [re.compile(p, re.IGNORECASE) for p in ANTI_A11Y_PATTERNS]


def _matches(content: str, patterns: list[re.Pattern]) -> list[str]:
    return sorted({p.pattern for p in patterns if p.search(content)})


def classify_file_a11y(path: str, content: str) -> dict[str, Any]:
    return {
        "anti_a11y_patterns": _matches(content, ANTI_C),
        "aria_usage": _matches(content, ARIA_C),
        "asl_references": _matches(content, ASL_C),
        "caption_handling": _matches(content, CAPTION_C),
        "path": path,
        "visual_first": _matches(content, VISUAL_C),
        "wcag_references": _matches(content, WCAG_C),
    }


def _score_file(classified: dict[str, Any]) -> int:
    """Simple additive a11y score. Higher = more a11y aware."""
    score = 0
    score += len(classified["aria_usage"]) * 2
    score += len(classified["asl_references"]) * 3
    score += len(classified["caption_handling"]) * 2
    score += len(classified["visual_first"]) * 2
    score += len(classified["wcag_references"]) * 3
    score -= len(classified["anti_a11y_patterns"]) * 5
    return max(score, 0)


def classify_accessibility_nodes(
    normalized: dict[str, Any],
    file_contents: dict[str, str],
) -> dict[str, Any]:
    """
    Run accessibility node classification across all normalized files.

    Args:
        normalized: Output from normalizer.normalize_inputs()
        file_contents: Dict of {relative_path: file_content_string}

    Returns:
        Sorted, deterministic a11y audit result.
    """
    results: list[dict[str, Any]] = []
    asl_files: list[str] = []
    caption_files: list[str] = []
    anti_a11y_files: list[str] = []
    total_score = 0

    for file_entry in normalized["files"]:
        path = file_entry["path"]
        content = file_contents.get(path, "")
        classified = classify_file_a11y(path, content)
        score = _score_file(classified)
        total_score += score

        if classified["asl_references"]:
            asl_files.append(path)
        if classified["caption_handling"]:
            caption_files.append(path)
        if classified["anti_a11y_patterns"]:
            anti_a11y_files.append(path)

        has_signal = score > 0 or classified["anti_a11y_patterns"]
        if has_signal:
            results.append({**classified, "a11y_score": score})

    results.sort(key=lambda r: r["path"])

    deaf_first_status = "STRONG" if len(asl_files) >= 3 else \
                        "PRESENT" if len(asl_files) >= 1 else "ABSENT"

    return {
        "anti_a11y_file_paths": sorted(anti_a11y_files),
        "asl_file_paths": sorted(asl_files),
        "caption_file_paths": sorted(caption_files),
        "deaf_first_status": deaf_first_status,
        "files_with_a11y": results,
        "schema_version": SCHEMA_VERSION,
        "summary": {
            "anti_a11y_files": len(anti_a11y_files),
            "asl_files": len(asl_files),
            "caption_files": len(caption_files),
            "total_a11y_score": total_score,
        },
    }


# ── Unit test stubs ──────────────────────────────────────────────────────────

def _test_asl_detected() -> None:
    result = classify_file_a11y("src/sign.tsx", "const lang = 'ASL'; // Deaf-First")
    assert result["asl_references"]
    print("PASS: asl_detected")


def _test_aria_detected() -> None:
    result = classify_file_a11y("src/button.tsx", '<button aria-label="Close">')
    assert result["aria_usage"]
    print("PASS: aria_detected")


def _test_anti_a11y() -> None:
    result = classify_file_a11y("src/legacy.html", "<marquee>Welcome</marquee>")
    assert result["anti_a11y_patterns"]
    print("PASS: anti_a11y")


if __name__ == "__main__":
    _test_asl_detected()
    _test_aria_detected()
    _test_anti_a11y()
    print("All accessibility_nodes tests passed.")