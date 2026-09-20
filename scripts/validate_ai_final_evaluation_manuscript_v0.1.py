#!/usr/bin/env python3
"""Validate R4 prose against frozen R1/R2/R3 authority files."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

EXPECTED = {
    "AI_FINAL_EVALUATION_INTERPRETATION_AUDIT_v0.1.md": "caf9e9e0bdf5c48484e71221ca0387949b3c30df",
    "AI_FINAL_EVALUATION_SECONDARY_AUDIT_v0.1.md": "edf25c29c7ef9a19b06c1f9c338597fc1e3fd313",
    "AI_FINAL_EVALUATION_PRESENTATION_PROTOCOL_v0.1.md": "51f5380e4c6f63fc82cb2ed6919d04c199db7d95",
    "outputs/manuscript_v0.1/table_primary_interactions.md": "1ef38f89cee573d2a3033ea7e502c96f51dd1e03",
    "outputs/manuscript_v0.1/table_exploratory_interactions.md": "52c189993f0f91ecd7f8f21f186d6dcad78eb071",
}
REQUIRED_MARKERS = tuple(f"[{x}]" for x in (
    "P1","P2","P3","P4","P5","E1","E2","R3","M1","M2","M3","L1","L2"
))
FORBIDDEN = (
    r"statistically significant",
    r"statistically insignificant",
    r"\bp[- ]?value\b",
    r"\bp\s*[<=>]\s*0\.",
    r"\bconverged policy\b",
    r"\boptimal policy\b",
    r"\bproves?\b",
    r"\bAI is better\b",
    r"\bfull transparency is better\b",
)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def validate_frozen_authorities(root: Path) -> None:
    for rel, expected in EXPECTED.items():
        path = root / rel
        if git_blob_sha(path) != expected:
            raise ValueError(f"frozen authority blob mismatch: {rel}")


def validate_prose(path: Path, claim_registry: Path) -> None:
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()

    for pattern in FORBIDDEN:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            raise ValueError(f"forbidden R4 wording: {pattern}")

    if "learned policies under the pre-registered finite training budget" not in text:
        raise ValueError("finite-budget wording missing")
    if "EXPLORATORY" not in text or "PRIMARY" not in text:
        raise ValueError("PRIMARY/EXPLORATORY labeling missing")
    if "Only 1 of the 15 AI training runs" not in text:
        raise ValueError("1/15 training-stability disclosure missing")
    if "remaining 14" not in text:
        raise ValueError("14/15 training-stability disclosure missing")

    for marker in REQUIRED_MARKERS:
        if marker not in text:
            raise ValueError(f"traceability marker missing: {marker}")

    claims = json.loads(claim_registry.read_text(encoding="utf-8"))
    registered = set(claims.get("claims", {}))
    expected = {x.strip("[]") for x in REQUIRED_MARKERS}
    if registered != expected:
        raise ValueError("claim registry key set mismatch")

    exploratory_pos = text.find("### 4.5 EXPLORATORY supporting results")
    discussion_pos = text.find("## 5. Discussion")
    if exploratory_pos < 0 or discussion_pos < 0 or exploratory_pos > discussion_pos:
        raise ValueError("exploratory subsection placement invalid")

    # Headline values must be copied exactly from frozen manuscript tables.
    required_literals = (
        "-18.367599",
        "[-49.124749, -1.245426]",
        "0.150154",
        "[0.004007, 0.361032]",
        "-18.904744",
        "[-49.059334, -2.075621]",
        "-3604.440665",
        "[-8664.310721, -96.279457]",
    )
    for literal in required_literals:
        if literal not in text:
            raise ValueError(f"required frozen value missing: {literal}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--prose", type=Path, default=Path("manuscript/AI_FINAL_EVALUATION_RESULTS_DISCUSSION_v0.1.md"))
    p.add_argument("--claims", type=Path, default=Path("experiments/ai_final_evaluation_manuscript_claim_registry_v0.1.json"))
    args = p.parse_args()
    validate_frozen_authorities(args.root)
    validate_prose(args.root / args.prose, args.root / args.claims)


if __name__ == "__main__":
    main()
