#!/usr/bin/env python3
"""Reproduce R2 secondary/exploratory summaries from frozen inputs only."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SECONDARY = (
    "retail_order_bullwhip",
    "total_lost_sales",
    "total_waste",
    "mean_abs_stock_allocation_gap_exporter_average",
)
REGIMES = ("N", "S", "F")
TRAINING_SEEDS = (41001, 41002, 41003, 41004, 41005)

EXPECTED_PANEL_SHA256 = "6ed8bbd779bf25f6f7370ee2e27439ce18915be98a9169d10dd1f08f6cf8c00c"
EXPECTED_RESULT_FREEZE_SHA = "7ea4ff9099525d1ee221905380f665f6d7627ff3"
EXPECTED_INTERPRETATION_FREEZE_SHA = "ece7fd704e0e3151e3a5ef02bf660a9d5e343c8b"
EXPECTED_ANALYSIS_BLOB_SHA = "d85cc1b9f673d0ecd801f9eb12142e9e861aecc2"
EXPECTED_R1_PROTOCOL_BLOB_SHA = "31a0add030441cf3556420b5932b6b6f5d4c3a58"
EXPECTED_EVALUATOR_SHA = "9e42c4a39e6bc8be94d1ed44e993899e4d916481"
EXPECTED_REGISTRY_SHA256 = "0ca89c10fc3135c577aca67f6d2ae573b72281b430218674dad5734ce72c686a"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_frozen_code(repo_root: Path) -> None:
    analysis = repo_root / "src/paper2_model0/ai/evaluation_analysis.py"
    r1_protocol = repo_root / "AI_FINAL_EVALUATION_INTERPRETATION_PROTOCOL_v0.1.md"
    if git_blob_sha(analysis) != EXPECTED_ANALYSIS_BLOB_SHA:
        raise ValueError("frozen analysis source blob mismatch")
    if git_blob_sha(r1_protocol) != EXPECTED_R1_PROTOCOL_BLOB_SHA:
        raise ValueError("R1 interpretation protocol blob mismatch")


def load_panel(path: Path) -> pd.DataFrame:
    if sha256_file(path) != EXPECTED_PANEL_SHA256:
        raise ValueError("frozen panel SHA-256 mismatch")
    frame = pd.read_json(path, lines=True)
    if len(frame) != 3600 or set(frame.scenario_index) != set(range(200)):
        raise ValueError("expected complete frozen 3,600-row panel")
    if not (frame.groupby("scenario_index").size() == 18).all():
        raise ValueError("expected 18 rows per scenario")
    if frame.source_sha.nunique() != 1 or frame.source_sha.iloc[0] != EXPECTED_EVALUATOR_SHA:
        raise ValueError("evaluator provenance mismatch")
    if frame.registry_sha256.nunique() != 1 or frame.registry_sha256.iloc[0] != EXPECTED_REGISTRY_SHA256:
        raise ValueError("checkpoint registry provenance mismatch")
    if not np.isfinite(frame[list(SECONDARY)].to_numpy(dtype=float)).all():
        raise ValueError("secondary outcomes must be finite and complete")

    expected = {(r, "RuleBased", None) for r in REGIMES} | {
        (r, "AI", s) for r in REGIMES for s in TRAINING_SEEDS
    }
    for _, group in frame.groupby("scenario_index"):
        keys = set()
        for row in group.itertuples():
            seed = None if pd.isna(row.training_seed) else int(row.training_seed)
            key = (str(row.regime), str(row.decision_architecture), seed)
            if key in keys:
                raise ValueError("duplicate treatment-policy row")
            keys.add(key)
        if keys != expected:
            raise ValueError("missing or unexpected treatment-policy row")
    return frame


def absolute_and_within(frame: pd.DataFrame, metric: str) -> dict:
    rb = {
        r: float(frame[(frame.regime == r) & (frame.decision_architecture == "RuleBased")][metric].mean())
        for r in REGIMES
    }
    ai = {
        r: float(frame[(frame.regime == r) & (frame.decision_architecture == "AI")][metric].mean())
        for r in REGIMES
    }
    return {
        "absolute_means": {
            "RuleBased": rb,
            "AI_pooled_over_five_frozen_training_seeds": ai,
        },
        "within_architecture_contrasts": {
            "RuleBased": {"S_minus_N": rb["S"] - rb["N"], "F_minus_S": rb["F"] - rb["S"]},
            "AI_pooled": {"S_minus_N": ai["S"] - ai["N"], "F_minus_S": ai["F"] - ai["S"]},
        },
    }


def build_summary(frame: pd.DataFrame) -> dict:
    module = importlib.import_module("paper2_model0.ai.evaluation_analysis")
    out = {
        "summary_version": "ai-final-evaluation-secondary-v0.1",
        "status": "R2_EXPLORATORY_ONLY",
        "frozen_inputs": {
            "result_freeze_sha": EXPECTED_RESULT_FREEZE_SHA,
            "interpretation_freeze_sha": EXPECTED_INTERPRETATION_FREEZE_SHA,
            "panel_jsonl_sha256": EXPECTED_PANEL_SHA256,
            "analysis_git_blob_sha": EXPECTED_ANALYSIS_BLOB_SHA,
        },
        "secondary_results": {},
    }
    for metric in SECONDARY:
        base = absolute_and_within(frame, metric)
        interaction = module.paired_bootstrap(*module.panel_arrays(frame, metric))
        base["frozen_exploratory_interactions"] = interaction
        out["secondary_results"][metric] = base
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--panel", type=Path, required=True)
    p.add_argument("--output", required=True, help="JSON path or '-' for stdout")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    verify_frozen_code(repo_root)
    frame = load_panel(args.panel)
    payload = json.dumps(build_summary(frame), sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.output == "-":
        print(payload, end="")
        return
    dest = Path(args.output)
    if dest.exists():
        raise FileExistsError(f"refusing to overwrite {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
