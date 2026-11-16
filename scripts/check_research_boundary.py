#!/usr/bin/env python3
"""Fail CI if legacy Paper-2 files or ambiguous dataset labels enter the CHAR tree."""
from pathlib import PurePosixPath
import subprocess

tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
required = {
    "README.md",
    "foundry.toml",
    "src/MockPool.sol",
    "test/SourceCHARBoundary.t.sol",
    "scripts/snapshot_base.sh",
    ".github/workflows/char-refi-foundry.yml",
    "docs/RESEARCH_BOUNDARY.md",
    "data/README.md",
}
missing = sorted(required - set(tracked))
legacy_prefixes = (
    "experiments/", "outputs/", "paper2_model0/",
    "paper_2_model0/", "src/paper2_model0/",
    "scripts/run_baseline.py", "scripts/run_deterministic_demo.py",
)
legacy = sorted(p for p in tracked if p.startswith(legacy_prefixes))
ambiguous = sorted(
    p for p in tracked
    if p.lower().endswith((".csv", ".parquet", ".feather"))
    and ("synthetic" not in PurePosixPath(p).name.lower())
    and not p.startswith("data/raw_onchain/")
    and not p.startswith("data/external/")
)
if missing or legacy or ambiguous:
    print("RESEARCH_BOUNDARY_FAIL")
    print("Missing required CHAR files:", missing)
    print("Legacy Paper-2 files:", legacy)
    print("Ambiguous quantitative files:", ambiguous)
    raise SystemExit(1)
print("RESEARCH_BOUNDARY_PASS")
print(f"{len(tracked)} tracked project files; no legacy code paths or ambiguous datasets.")
