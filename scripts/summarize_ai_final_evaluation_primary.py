#!/usr/bin/env python3
"""Read-only primary-result decomposition for the frozen Model-0 evaluation.

This module never simulates, trains, reloads a policy, changes a checkpoint,
or recomputes bootstrap confidence intervals. It verifies frozen inputs,
computes descriptive means/contrasts, and reproduces frozen interaction point
estimates and seed means.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

PRIMARY = (
    "service_level",
    "waste_share_of_terminal_outflow",
    "importer_procurement_bullwhip",
    "mean_total_inventory",
    "mean_abs_target_allocation_gap_exporter_average",
)
REGIMES = ("N", "S", "F")
TRAINING_SEEDS = (41001, 41002, 41003, 41004, 41005)

EXPECTED_PANEL_SHA256 = "6ed8bbd779bf25f6f7370ee2e27439ce18915be98a9169d10dd1f08f6cf8c00c"
EXPECTED_RESULT_REGISTRY_BLOB_SHA = "40d590f742c85f7e853bd3766a41fc335510b4b9"
EXPECTED_TRAINING_REGISTRY_BLOB_SHA = "ded174d7c9ffd23d15f0ec53767861bf641b993b"
EXPECTED_EVALUATOR_SHA = "9e42c4a39e6bc8be94d1ed44e993899e4d916481"
EXPECTED_TRAINING_REGISTRY_SHA256 = "0ca89c10fc3135c577aca67f6d2ae573b72281b430218674dad5734ce72c686a"
RESULT_FREEZE_SHA = "7ea4ff9099525d1ee221905380f665f6d7627ff3"
FROZEN_ANALYSIS_BLOB_SHA = "d85cc1b9f673d0ecd801f9eb12142e9e861aecc2"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_blob_sha(path: Path) -> str:
    data = Path(path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def load_json_exact(path: Path, expected_blob_sha: str) -> dict:
    if git_blob_sha(path) != expected_blob_sha:
        raise ValueError(f"frozen Git blob mismatch: {path}")
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def load_panel(path: Path) -> pd.DataFrame:
    if sha256_file(path) != EXPECTED_PANEL_SHA256:
        raise ValueError("frozen panel SHA-256 mismatch")
    frame = pd.read_json(path, lines=True)

    if len(frame) != 3600:
        raise ValueError("expected exactly 3,600 panel rows")
    if set(frame["scenario_index"]) != set(range(200)):
        raise ValueError("expected exactly scenario indices 0..199")
    counts = frame.groupby("scenario_index").size()
    if not (counts == 18).all():
        raise ValueError("each scenario must contain exactly 18 treatment-policy rows")

    expected_keys = {(r, "RuleBased", None) for r in REGIMES} | {
        (r, "AI", s) for r in REGIMES for s in TRAINING_SEEDS
    }
    for _, group in frame.groupby("scenario_index"):
        keys = set()
        for row in group.itertuples():
            seed = None if pd.isna(row.training_seed) else int(row.training_seed)
            key = (str(row.regime), str(row.decision_architecture), seed)
            if key in keys:
                raise ValueError("duplicate treatment-policy row within scenario")
            keys.add(key)
        if keys != expected_keys:
            raise ValueError("missing or unexpected treatment-policy row within scenario")

    if frame["scenario_id"].nunique() != 200:
        raise ValueError("scenario IDs must be unique across 200 scenarios")
    if frame["evaluation_scenario_seed"].nunique() != 200:
        raise ValueError("evaluation scenario seeds must be unique")

    if set(frame["regime"]) != set(REGIMES):
        raise ValueError("unexpected information regime")
    if set(frame["decision_architecture"]) != {"RuleBased", "AI"}:
        raise ValueError("unexpected decision architecture")
    if len(frame[frame["decision_architecture"] == "RuleBased"]) != 600:
        raise ValueError("expected 600 RuleBased rows")
    if len(frame[frame["decision_architecture"] == "AI"]) != 3000:
        raise ValueError("expected 3,000 AI rows")

    ai_seeds = set(frame.loc[frame["decision_architecture"] == "AI", "training_seed"].astype(int))
    if ai_seeds != set(TRAINING_SEEDS):
        raise ValueError("AI training-seed set drift")
    if frame.loc[frame["decision_architecture"] == "RuleBased", "training_seed"].notna().any():
        raise ValueError("RuleBased rows must not carry training seeds")

    if frame["source_sha"].nunique() != 1 or frame["source_sha"].iloc[0] != EXPECTED_EVALUATOR_SHA:
        raise ValueError("frozen evaluator provenance mismatch")
    if frame["registry_sha256"].nunique() != 1:
        raise ValueError("mixed checkpoint-registry provenance")
    if frame["registry_sha256"].iloc[0] != EXPECTED_TRAINING_REGISTRY_SHA256:
        raise ValueError("checkpoint-registry SHA-256 mismatch")

    if not np.isfinite(frame[list(PRIMARY)].to_numpy(dtype=float)).all():
        raise ValueError("primary outcomes must be finite and complete")
    return frame


def stability_map(training_registry: dict) -> dict[tuple[str, int], dict]:
    entries = training_registry.get("entries", [])
    result = {}
    for entry in entries:
        key = (str(entry["regime"]), int(entry["training_seed"]))
        if key in result:
            raise ValueError("duplicate training-registry entry")
        result[key] = {
            "training_stable": bool(entry["training_stable"]),
            "stability_label": str(entry["stability_label"]),
        }
    expected = {(r, s) for r in REGIMES for s in TRAINING_SEEDS}
    if set(result) != expected:
        raise ValueError("training-registry key set drift")
    if sum(v["training_stable"] for v in result.values()) != 1:
        raise ValueError("expected exactly one preregistered training-stable run")
    return result


def descriptive_metric(
    frame: pd.DataFrame,
    metric: str,
    frozen_metric: dict,
    stability: dict[tuple[str, int], dict],
) -> dict:
    if metric not in PRIMARY:
        raise ValueError("R1 is primary-only")

    rb = {
        regime: float(
            frame[
                (frame["regime"] == regime)
                & (frame["decision_architecture"] == "RuleBased")
            ][metric].mean()
        )
        for regime in REGIMES
    }
    ai_by_seed = {
        str(seed): {
            regime: float(
                frame[
                    (frame["regime"] == regime)
                    & (frame["decision_architecture"] == "AI")
                    & (frame["training_seed"] == seed)
                ][metric].mean()
            )
            for regime in REGIMES
        }
        for seed in TRAINING_SEEDS
    }
    ai_pooled = {
        regime: float(
            frame[
                (frame["regime"] == regime)
                & (frame["decision_architecture"] == "AI")
            ][metric].mean()
        )
        for regime in REGIMES
    }

    rb_v = rb["S"] - rb["N"]
    rb_h = rb["F"] - rb["S"]
    ai_v = ai_pooled["S"] - ai_pooled["N"]
    ai_h = ai_pooled["F"] - ai_pooled["S"]
    gamma_v = ai_v - rb_v
    gamma_h = ai_h - rb_h

    seed_decomposition = {}
    seed_gamma_v = []
    seed_gamma_h = []
    for seed in TRAINING_SEEDS:
        values = ai_by_seed[str(seed)]
        g_v = (values["S"] - values["N"]) - rb_v
        g_h = (values["F"] - values["S"]) - rb_h
        seed_gamma_v.append(g_v)
        seed_gamma_h.append(g_h)
        seed_decomposition[str(seed)] = {
            "AI_absolute_means": values,
            "Gamma_V": g_v,
            "Gamma_H": g_h,
            "stability": {
                regime: stability[(regime, seed)]
                for regime in REGIMES
            },
            "Gamma_V_both_endpoints_training_stable": (
                stability[("N", seed)]["training_stable"]
                and stability[("S", seed)]["training_stable"]
            ),
            "Gamma_H_both_endpoints_training_stable": (
                stability[("S", seed)]["training_stable"]
                and stability[("F", seed)]["training_stable"]
            ),
        }

    frozen_v = frozen_metric["Gamma_V"]
    frozen_h = frozen_metric["Gamma_H"]
    if not np.isclose(gamma_v, frozen_v["mean"], rtol=0.0, atol=1e-12):
        raise ValueError(f"{metric}: Gamma_V point estimate does not reproduce")
    if not np.isclose(gamma_h, frozen_h["mean"], rtol=0.0, atol=1e-12):
        raise ValueError(f"{metric}: Gamma_H point estimate does not reproduce")
    if not np.allclose(seed_gamma_v, frozen_v["seed_means"], rtol=0.0, atol=1e-12):
        raise ValueError(f"{metric}: Gamma_V seed means do not reproduce")
    if not np.allclose(seed_gamma_h, frozen_h["seed_means"], rtol=0.0, atol=1e-12):
        raise ValueError(f"{metric}: Gamma_H seed means do not reproduce")

    return {
        "absolute_means": {
            "RuleBased": rb,
            "AI_pooled_over_five_frozen_training_seeds": ai_pooled,
        },
        "within_architecture_contrasts": {
            "RuleBased": {"S_minus_N": rb_v, "F_minus_S": rb_h},
            "AI_pooled": {"S_minus_N": ai_v, "F_minus_S": ai_h},
        },
        "frozen_interactions": {
            "Gamma_V": {
                "mean": float(frozen_v["mean"]),
                "ci95": [float(x) for x in frozen_v["ci95"]],
                "between_seed_sd": float(frozen_v["between_seed_sd"]),
            },
            "Gamma_H": {
                "mean": float(frozen_h["mean"]),
                "ci95": [float(x) for x in frozen_h["ci95"]],
                "between_seed_sd": float(frozen_h["between_seed_sd"]),
            },
        },
        "seed_decomposition": seed_decomposition,
    }


def build_summary(
    panel: pd.DataFrame,
    result_registry: dict,
    training_registry: dict,
) -> dict:
    frozen_primary = result_registry.get("primary_results", {})
    if set(frozen_primary) != set(PRIMARY):
        raise ValueError("result registry primary metric set drift")
    stability = stability_map(training_registry)

    return {
        "summary_version": "ai-final-evaluation-primary-interpretation-v0.1",
        "status": "R1_PRIMARY_ONLY_DESCRIPTIVE_NO_NEW_INFERENCE",
        "frozen_inputs": {
            "result_freeze_sha": RESULT_FREEZE_SHA,
            "panel_jsonl_sha256": EXPECTED_PANEL_SHA256,
            "result_registry_git_blob_sha": EXPECTED_RESULT_REGISTRY_BLOB_SHA,
            "training_registry_git_blob_sha": EXPECTED_TRAINING_REGISTRY_BLOB_SHA,
            "frozen_primary_analysis_git_blob_sha": FROZEN_ANALYSIS_BLOB_SHA,
            "evaluator_sha": EXPECTED_EVALUATOR_SHA,
            "checkpoint_registry_sha256": EXPECTED_TRAINING_REGISTRY_SHA256,
        },
        "training_stability": {
            "training_stable_runs": 1,
            "not_stabilized_under_preregistered_budget": 14,
            "selection_or_exclusion_applied": False,
        },
        "scope": {
            "primary_metrics": list(PRIMARY),
            "secondary_metrics_included": False,
            "new_bootstrap_or_p_values": False,
        },
        "metrics": {
            metric: descriptive_metric(
                panel,
                metric,
                frozen_primary[metric],
                stability,
            )
            for metric in PRIMARY
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument(
        "--result-registry",
        type=Path,
        default=Path("experiments/ai_final_evaluation_result_registry_v0.1.json"),
    )
    parser.add_argument(
        "--training-registry",
        type=Path,
        default=Path("experiments/ai_training_checkpoint_registry_v0.1.json"),
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON path, or '-' for stdout. Existing files are never overwritten.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result_registry = load_json_exact(
        args.result_registry, EXPECTED_RESULT_REGISTRY_BLOB_SHA
    )
    training_registry = load_json_exact(
        args.training_registry, EXPECTED_TRAINING_REGISTRY_BLOB_SHA
    )
    if (
        result_registry.get("artifacts", {})
        .get("final_panel", {})
        .get("panel_jsonl_sha256")
        != EXPECTED_PANEL_SHA256
    ):
        raise ValueError("result registry does not bind the expected panel")

    panel = load_panel(args.panel)
    summary = build_summary(panel, result_registry, training_registry)
    payload = json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + "\n"

    if args.output == "-":
        print(payload, end="")
        return
    destination = Path(args.output)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
