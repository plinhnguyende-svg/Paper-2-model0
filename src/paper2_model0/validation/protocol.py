from __future__ import annotations

from dataclasses import replace
from typing import Iterable

import numpy as np
import pandas as pd

from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import generate_scenario
from paper2_model0.engine.model import SupplyChainModel
from paper2_model0.experiments.metrics import replication_metrics
from paper2_model0.experiments.runner import run_paired_experiment


DEFAULT_EFFECTS = ("S_minus_N", "F_minus_S")


def summarize_paired_effects(
    paired_df: pd.DataFrame,
    effects: Iterable[str] = DEFAULT_EFFECTS,
) -> pd.DataFrame:
    rows: list[dict] = []
    if paired_df.empty:
        return pd.DataFrame(
            columns=["metric", "effect", "mean", "sd", "ci95_low", "ci95_high", "n"]
        )

    for metric, group in paired_df.groupby("metric"):
        for effect in effects:
            if effect not in group.columns:
                continue
            values = group[effect].dropna().astype(float)
            n = len(values)
            mean = float(values.mean()) if n else float("nan")
            sd = float(values.std(ddof=1)) if n > 1 else float("nan")
            half = 1.96 * sd / np.sqrt(n) if n > 1 else float("nan")
            rows.append(
                {
                    "metric": metric,
                    "effect": effect,
                    "mean": mean,
                    "sd": sd,
                    "ci95_low": mean - half if n > 1 else float("nan"),
                    "ci95_high": mean + half if n > 1 else float("nan"),
                    "n": n,
                }
            )
    return pd.DataFrame(rows)


def classify_ci_direction(ci95_low: float, ci95_high: float) -> str:
    if np.isnan(ci95_low) or np.isnan(ci95_high):
        return "insufficient"
    if ci95_low > 0:
        return "positive"
    if ci95_high < 0:
        return "negative"
    return "overlaps_zero"


def apply_parameter(config: SimulationConfig, name: str, value) -> SimulationConfig:
    if name == "exporter_availability_probability_symmetric":
        updated = replace(
            config,
            exporter_availability_probability=(float(value), float(value)),
        )
    elif name in {
        "shelf_life_days",
        "exporter_to_importer_lead_time_days",
        "importer_to_retailer_lead_time_days",
        "simulation_horizon_days",
        "warmup_days",
    }:
        updated = replace(config, **{name: int(value)})
    elif name == "demand_forecast_smoothing_weight":
        updated = replace(config, **{name: float(value)})
    else:
        raise ValueError(
            f"Unsupported validation factor {name!r}. "
            "Add it explicitly so Model 0 is not silently extended."
        )
    updated.validate()
    return updated


def _paired_rows_from_replication_metrics(
    replication_rows: list[dict],
    regimes: tuple[str, ...] = ("N", "S", "F"),
) -> pd.DataFrame:
    replication_df = pd.DataFrame(replication_rows)
    id_cols = {"replication_id", "scenario_id", "replication_seed", "regime"}
    metrics = [c for c in replication_df.columns if c not in id_cols]
    paired_rows: list[dict] = []
    keys = ["replication_id", "scenario_id", "replication_seed"]

    for metric in metrics:
        wide = replication_df.pivot(index=keys, columns="regime", values=metric).reset_index()
        for _, row in wide.iterrows():
            entry = {
                "replication_id": int(row["replication_id"]),
                "scenario_id": row["scenario_id"],
                "replication_seed": int(row["replication_seed"]),
                "metric": metric,
            }
            for regime in regimes:
                if regime in wide.columns:
                    entry[f"{regime}_value"] = row[regime]
            if "N" in regimes and "S" in regimes:
                entry["S_minus_N"] = row["S"] - row["N"]
            if "S" in regimes and "F" in regimes:
                entry["F_minus_S"] = row["F"] - row["S"]
            if "N" in regimes and "F" in regimes:
                entry["F_minus_N"] = row["F"] - row["N"]
            paired_rows.append(entry)
    return pd.DataFrame(paired_rows)


def warmup_convergence_diagnostic(
    base_config: SimulationConfig,
    *,
    warmup_candidates_days: Iterable[int],
    measurement_window_days: int,
    number_of_replications: int,
    master_seed: int,
    regimes: tuple[str, ...] = ("N", "S", "F"),
) -> pd.DataFrame:
    candidates = sorted({int(x) for x in warmup_candidates_days})
    if not candidates or candidates[0] < 0:
        raise ValueError("warm-up candidates must be nonnegative")
    if measurement_window_days <= 1:
        raise ValueError("measurement_window_days must exceed 1")

    horizon = max(candidates) + int(measurement_window_days)
    config = replace(base_config, simulation_horizon_days=horizon, warmup_days=0)
    config.validate()

    root_ss = np.random.SeedSequence(master_seed)
    rep_children = root_ss.spawn(number_of_replications)
    period_cache: dict[tuple[int, str], pd.DataFrame] = {}
    scenario_meta: dict[int, tuple[str, int]] = {}

    for rep_id, rep_ss in enumerate(rep_children):
        rep_seed = int(rep_ss.generate_state(1, dtype=np.uint64)[0])
        scenario = generate_scenario(config, rep_seed)
        scenario_meta[rep_id] = (scenario.scenario_id, rep_seed)
        for regime in regimes:
            period_cache[(rep_id, regime)] = SupplyChainModel(
                config, regime, scenario
            ).run()

    output_rows: list[dict] = []
    for warmup in candidates:
        replication_rows: list[dict] = []
        end_day = warmup + measurement_window_days
        for rep_id in range(number_of_replications):
            scenario_id, rep_seed = scenario_meta[rep_id]
            for regime in regimes:
                window_df = period_cache[(rep_id, regime)]
                window_df = window_df.loc[window_df["day"] < end_day]
                metrics = replication_metrics(window_df, warmup)
                replication_rows.append(
                    {
                        "replication_id": rep_id,
                        "scenario_id": scenario_id,
                        "replication_seed": rep_seed,
                        "regime": regime,
                        **metrics,
                    }
                )

        paired_df = _paired_rows_from_replication_metrics(replication_rows, regimes)
        summary = summarize_paired_effects(paired_df)
        for row in summary.to_dict("records"):
            output_rows.append(
                {
                    "warmup_days": warmup,
                    "measurement_window_days": measurement_window_days,
                    **row,
                    "direction": classify_ci_direction(
                        row["ci95_low"], row["ci95_high"]
                    ),
                }
            )
    return pd.DataFrame(output_rows)


def replication_sufficiency_diagnostic(
    config: SimulationConfig,
    *,
    max_replications: int,
    checkpoints: Iterable[int],
    master_seed: int,
) -> pd.DataFrame:
    checkpoints = sorted({int(x) for x in checkpoints})
    if not checkpoints or checkpoints[0] < 2:
        raise ValueError("replication checkpoints must be >= 2")
    if checkpoints[-1] > max_replications:
        raise ValueError("checkpoint exceeds max_replications")

    _, paired_df = run_paired_experiment(
        config,
        number_of_replications=max_replications,
        master_seed=master_seed,
    )

    rows: list[dict] = []
    for n in checkpoints:
        subset = paired_df.loc[paired_df["replication_id"] < n]
        summary = summarize_paired_effects(subset)
        for row in summary.to_dict("records"):
            half_width = (
                (row["ci95_high"] - row["ci95_low"]) / 2.0
                if row["n"] > 1
                else float("nan")
            )
            rows.append(
                {
                    "replications": n,
                    **row,
                    "ci95_half_width": half_width,
                    "direction": classify_ci_direction(
                        row["ci95_low"], row["ci95_high"]
                    ),
                }
            )
    return pd.DataFrame(rows)


def seed_stability_diagnostic(
    config: SimulationConfig,
    *,
    master_seeds: Iterable[int],
    number_of_replications: int,
) -> pd.DataFrame:
    rows: list[dict] = []
    for seed in master_seeds:
        _, paired_df = run_paired_experiment(
            config,
            number_of_replications=number_of_replications,
            master_seed=int(seed),
        )
        summary = summarize_paired_effects(paired_df)
        for row in summary.to_dict("records"):
            rows.append(
                {
                    "master_seed": int(seed),
                    **row,
                    "direction": classify_ci_direction(
                        row["ci95_low"], row["ci95_high"]
                    ),
                }
            )
    return pd.DataFrame(rows)


def ofat_diagnostic(
    base_config: SimulationConfig,
    *,
    factor_name: str,
    values: Iterable,
    number_of_replications: int,
    master_seed: int,
) -> pd.DataFrame:
    rows: list[dict] = []
    for value in values:
        config = apply_parameter(base_config, factor_name, value)
        _, paired_df = run_paired_experiment(
            config,
            number_of_replications=number_of_replications,
            master_seed=master_seed,
        )
        summary = summarize_paired_effects(paired_df)
        for row in summary.to_dict("records"):
            rows.append(
                {
                    "factor": factor_name,
                    "value": value,
                    **row,
                    "direction": classify_ci_direction(
                        row["ci95_low"], row["ci95_high"]
                    ),
                }
            )
    return pd.DataFrame(rows)


def phase_map_diagnostic(
    base_config: SimulationConfig,
    *,
    x_name: str,
    x_values: Iterable,
    y_name: str,
    y_values: Iterable,
    number_of_replications: int,
    master_seed: int,
) -> pd.DataFrame:
    rows: list[dict] = []
    for x in x_values:
        for y in y_values:
            config = apply_parameter(base_config, x_name, x)
            config = apply_parameter(config, y_name, y)
            _, paired_df = run_paired_experiment(
                config,
                number_of_replications=number_of_replications,
                master_seed=master_seed,
            )
            summary = summarize_paired_effects(paired_df)
            for row in summary.to_dict("records"):
                rows.append(
                    {
                        "x_name": x_name,
                        "x_value": x,
                        "y_name": y_name,
                        "y_value": y,
                        **row,
                        "direction": classify_ci_direction(
                            row["ci95_low"], row["ci95_high"]
                        ),
                    }
                )
    return pd.DataFrame(rows)
