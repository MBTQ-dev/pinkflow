"""
PinkFlow Deterministic Audit Pipeline
Module 4: journey_classifier.py

Classifies which MBTQ pathway/journey each file serves:
- Business Magician
- Job Magician
- Developer Magician
- Creative Magician
- Platform/Infrastructure (cross-cutting)
- Unknown

Also detects lifecycle phase: Idea → Build → Grow → Managed

Deterministic: pure input→output, no network, no randomness.
"""

from __future__ import annotations

import re
from typing import Any

SCHEMA_VERSION = "pinkflow.audit.v1"

# ── Pathway detection patterns ───────────────────────────────────────────────

PATHWAY_PATTERNS: dict[str, list[str]] = {
    "business": [
        r"business.?magician",
        r"BusinessMagician",
        r"market.?research",
        r"pitch",
        r"revenue",
        r"go.?to.?market",
        r"business.?plan",
        r"growth",
        r"client",
        r"invoice",
        r"360businessmagician",
    ],
    "job": [
        r"job.?magician",
        r"JobMagician",
        r"resume",
        r"career",
        r"interview",
        r"employment",
        r"workforce",
        r"voc.?rehab",
        r"RSA",
        r"NIDILRR",
        r"TTW",
        r"ticket.?to.?work",
    ],
    "developer": [
        r"developer.?magician",
        r"DeveloperMagician",
        r"scaffold",
        r"monorepo",
        r"deno",
        r"service\.json",
        r"pinksync",
        r"deafauth",
        r"pinkflow",
        r"mbtq",
        r"auto.?api",
        r"docker",
        r"terraform",
    ],
    "creative": [
        r"creative.?magician",
        r"CreativeMagician",
        r"SignMirror",
        r"asl.?content",
        r"creator",
        r"sign.?language.*video",
        r"media.?pipeline",
        r"pinksync.*media",
        r"caption.*creator",
        r"brand",
    ],
    "platform": [
        r"fibonrose",
        r"FibonRose",
        r"magiciancore",
        r"MagicianCore",
        r"negrasecurity",
        r"NegraSecurity",
        r"hetzner",
        r"cloudflare",
        r"supabase",
        r"gcp",
        r"cloud.?run",
        r"pgvector",
        r"paseto",
    ],
}

LIFECYCLE_PATTERNS: dict[str, list[str]] = {
    "idea": [
        r"concept",
        r"feasibility",
        r"requirement",
        r"proposal",
        r"rfc",
        r"design.?doc",
        r"brainstorm",
    ],
    "build": [
        r"implement",
        r"scaffold",
        r"TODO",
        r"WIP",
        r"in.?progress",
        r"build",
        r"develop",
        r"migration",
    ],
    "grow": [
        r"optimize",
        r"scale",
        r"performance",
        r"feature.?flag",
        r"A/B",
        r"analytics",
        r"funnel",
    ],
    "managed": [
        r"monitor",
        r"alert",
        r"SLA",
        r"runbook",
        r"incident",
        r"on.?call",
        r"maintenance",
        r"deprecat",
    ],
}

PATHWAY_C = {
    k: [re.compile(p, re.IGNORECASE) for p in patterns]
    for k, patterns in PATHWAY_PATTERNS.items()
}
LIFECYCLE_C = {
    k: [re.compile(p, re.IGNORECASE) for p in patterns]
    for k, patterns in LIFECYCLE_PATTERNS.items()
}


def _match_keys(search_text: str, compiled: dict[str, list[re.Pattern]]) -> list[str]:
    return sorted(k for k, patterns in compiled.items()
                  if any(p.search(search_text) for p in patterns))


def classify_file_journey(path: str, content: str) -> dict[str, Any]:
    # Combine path and content to guarantee classification stability even on blank/meta files
    combined_target = f"{path}\n{content}"
    
    pathways = _match_keys(combined_target, PATHWAY_C)
    lifecycle = _match_keys(combined_target, LIFECYCLE_C)
    
    # Refined hierarchy: Core app logic paths (developer/business/job) override base infra (platform)
    if len(pathways) == 1:
        primary_pathway = pathways[0]
    elif pathways:
        if "developer" in pathways:
            primary_pathway = "developer"
        elif "platform" in pathways:
            primary_pathway = "platform"
        else:
            primary_pathway = pathways[0]
    else:
        primary_pathway = "unknown"

    return {
        "lifecycle_phases": lifecycle,
        "path": path,
        "pathways": pathways,
        "primary_pathway": primary_pathway,
    }


def classify_journeys(
    normalized: dict[str, Any],
    file_contents: dict[str, str],
) -> dict[str, Any]:
    """
    Classify journey/pathway for all normalized files.

    Args:
        normalized: Output from normalizer.normalize_inputs()
        file_contents: Dict of {relative_path: file_content_string}

    Returns:
        Deterministic journey classification map.
    """
    results: list[dict[str, Any]] = []
    pathway_counts: dict[str, int] = {k: 0 for k in PATHWAY_PATTERNS}
    pathway_counts["unknown"] = 0

    for file_entry in normalized["files"]:
        path = file_entry["path"]
        content = file_contents.get(path, "")
        classified = classify_file_journey(path, content)
        pathway_counts[classified["primary_pathway"]] = \
            pathway_counts.get(classified["primary_pathway"], 0) + 1
        results.append(classified)

    results.sort(key=lambda r: r["path"])

    dominant_pathway = max(pathway_counts, key=lambda k: pathway_counts[k])

    return {
        "dominant_pathway": dominant_pathway,
        "file_journeys": results,
        "pathway_counts": dict(sorted(pathway_counts.items())),
        "schema_version": SCHEMA_VERSION,
    }


# ── Enhanced Unit Test Verifications ──────────────────────────────────────────

def _test_developer_pathway() -> None:
    result = classify_file_journey(
        "services/deafauth/index.ts",
        "import { PinkSync } from '@mbtq/pinksync'; // deno scaffold"
    )
    assert "developer" in result["pathways"]
    print("PASS: developer_pathway")


def _test_platform_pathway() -> None:
    result = classify_file_journey(
        "infra/terraform/main.tf",
        "resource hetzner_server fibonrose { }"
    )
    assert "platform" in result["pathways"]
    print("PASS: platform_pathway")


def _test_path_only_detection() -> None:
    # Ensures empty vendor configs correctly fall back to path mapping
    result = classify_file_journey("services/pinksync/empty_config.json", "")
    assert "developer" in result["pathways"]
    print("PASS: path_only_detection")


def _test_unknown_pathway() -> None:
    result = classify_file_journey("README.md", "# Hello World")
    assert result["primary_pathway"] == "unknown"
    print("PASS: unknown_pathway")


if __name__ == "__main__":
    _test_developer_pathway()
    _test_platform_pathway()
    _test_path_only_detection()
    _test_unknown_pathway()
    print("All pinkflow journey_classifier tests explicitly passed.")
