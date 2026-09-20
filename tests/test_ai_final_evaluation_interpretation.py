from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "summarize_ai_final_evaluation_primary.py"
SPEC = importlib.util.spec_from_file_location("r1_summary", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def _synthetic_panel():
    rows = []
    for scenario in range(2):
        for regime_index, regime in enumerate(MOD.REGIMES):
            rows.append(
                {
                    "scenario_index": scenario,
                    "regime": regime,
                    "decision_architecture": "RuleBased",
                    "training_seed": np.nan,
                    "metric": 10.0 + regime_index + scenario,
                }
            )
            for seed_index, seed in enumerate(MOD.TRAINING_SEEDS):
                rows.append(
                    {
                        "scenario_index": scenario,
                        "regime": regime,
                        "decision_architecture": "AI",
                        "training_seed": seed,
                        "metric": 20.0 + 2 * regime_index + seed_index + scenario,
                    }
                )
    return pd.DataFrame(rows)


def test_descriptive_metric_uses_all_five_seeds_and_reproduces_interactions():
    frame = _synthetic_panel()
    rb = {
        r: frame[
            (frame.regime == r) & (frame.decision_architecture == "RuleBased")
        ].metric.mean()
        for r in MOD.REGIMES
    }
    seed_means_v = []
    seed_means_h = []
    for seed in MOD.TRAINING_SEEDS:
        ai = {
            r: frame[
                (frame.regime == r)
                & (frame.decision_architecture == "AI")
                & (frame.training_seed == seed)
            ].metric.mean()
            for r in MOD.REGIMES
        }
        seed_means_v.append((ai["S"] - ai["N"]) - (rb["S"] - rb["N"]))
        seed_means_h.append((ai["F"] - ai["S"]) - (rb["F"] - rb["S"]))
    frozen = {
        "Gamma_V": {
            "mean": float(np.mean(seed_means_v)),
            "ci95": [-1.0, 1.0],
            "between_seed_sd": 0.0,
            "seed_means": seed_means_v,
        },
        "Gamma_H": {
            "mean": float(np.mean(seed_means_h)),
            "ci95": [-1.0, 1.0],
            "between_seed_sd": 0.0,
            "seed_means": seed_means_h,
        },
    }
    stability = {
        (r, s): {
            "training_stable": (r, s) == ("N", 41003),
            "stability_label": (
                "training-stable"
                if (r, s) == ("N", 41003)
                else "not stabilized under the pre-registered budget"
            ),
        }
        for r in MOD.REGIMES
        for s in MOD.TRAINING_SEEDS
    }

    result = MOD.descriptive_metric(
        frame.rename(columns={"metric": "service_level"}),
        "service_level",
        frozen,
        stability,
    )

    assert len(result["seed_decomposition"]) == 5
    assert result["seed_decomposition"]["41003"]["stability"]["N"]["training_stable"]
    assert not result["seed_decomposition"]["41003"]["Gamma_V_both_endpoints_training_stable"]
    assert not result["seed_decomposition"]["41003"]["Gamma_H_both_endpoints_training_stable"]
    assert np.isclose(result["frozen_interactions"]["Gamma_V"]["mean"], np.mean(seed_means_v))
    assert np.isclose(result["frozen_interactions"]["Gamma_H"]["mean"], np.mean(seed_means_h))


def test_r1_primary_scope_is_exact_and_excludes_secondary_metrics():
    assert MOD.PRIMARY == (
        "service_level",
        "waste_share_of_terminal_outflow",
        "importer_procurement_bullwhip",
        "mean_total_inventory",
        "mean_abs_target_allocation_gap_exporter_average",
    )
    assert "retail_order_bullwhip" not in MOD.PRIMARY
    assert "total_lost_sales" not in MOD.PRIMARY
    assert "total_waste" not in MOD.PRIMARY
