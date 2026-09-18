from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import generate_scenario
from paper2_model0.engine.model import SupplyChainModel
from paper2_model0.experiments.metrics import replication_metrics


def config_hash(config: SimulationConfig) -> str:
    payload = json.dumps(asdict(config), sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def run_paired_experiment(
    config: SimulationConfig,
    *,
    number_of_replications: int,
    master_seed: int,
    regimes=("N", "S", "F"),
    save_period_level: bool = False,
    output_dir: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    config.validate()
    root_ss = np.random.SeedSequence(master_seed)
    rep_children = root_ss.spawn(number_of_replications)

    replication_rows = []
    period_frames = []

    for rep_id, rep_ss in enumerate(rep_children):
        # uint64-derived integer is stable and sufficient for downstream SeedSequence.
        rep_seed = int(rep_ss.generate_state(1, dtype=np.uint64)[0])
        scenario = generate_scenario(config, rep_seed)
        for regime in regimes:
            model = SupplyChainModel(config, regime, scenario)
            df = model.run()
            metrics = replication_metrics(df, config.warmup_days)
            replication_rows.append({
                "replication_id": rep_id,
                "scenario_id": scenario.scenario_id,
                "replication_seed": rep_seed,
                "regime": regime,
                **metrics,
            })
            if save_period_level:
                tmp = df.copy()
                tmp["replication_id"] = rep_id
                period_frames.append(tmp)

    replication_df = pd.DataFrame(replication_rows)

    metrics = [
        c for c in replication_df.columns
        if c not in {"replication_id", "scenario_id", "replication_seed", "regime"}
    ]
    paired_rows = []
    pivot_keys = ["replication_id", "scenario_id", "replication_seed"]
    for metric in metrics:
        wide = replication_df.pivot(index=pivot_keys, columns="regime", values=metric).reset_index()
        for _, row in wide.iterrows():
            entry = {
                "replication_id": int(row["replication_id"]),
                "scenario_id": row["scenario_id"],
                "replication_seed": int(row["replication_seed"]),
                "metric": metric,
            }
            for regime in regimes:
                entry[f"{regime}_value"] = row.get(regime, float("nan"))
            if "N" in regimes and "S" in regimes:
                entry["S_minus_N"] = row["S"] - row["N"]
            if "S" in regimes and "F" in regimes:
                entry["F_minus_S"] = row["F"] - row["S"]
            if "N" in regimes and "F" in regimes:
                entry["F_minus_N"] = row["F"] - row["N"]
            paired_rows.append(entry)
    paired_df = pd.DataFrame(paired_rows)

    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        replication_df.to_csv(out / "replication_level.csv", index=False)
        paired_df.to_csv(out / "paired_effects.csv", index=False)
        if period_frames:
            pd.concat(period_frames, ignore_index=True).to_csv(out / "period_level.csv", index=False)
        manifest = {
            "model_version": "model0_v0.1",
            "configuration_hash": config_hash(config),
            "master_seed": master_seed,
            "number_of_replications": number_of_replications,
            "regimes": list(regimes),
            "config": asdict(config),
        }
        with open(out / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    return replication_df, paired_df


def summarize_regimes(replication_df: pd.DataFrame) -> pd.DataFrame:
    metric_cols = [
        c for c in replication_df.columns
        if c not in {"replication_id", "scenario_id", "replication_seed", "regime"}
    ]
    rows = []
    for regime, group in replication_df.groupby("regime"):
        for metric in metric_cols:
            values = group[metric].dropna().astype(float)
            n = len(values)
            mean = float(values.mean()) if n else float("nan")
            sd = float(values.std(ddof=1)) if n > 1 else float("nan")
            half = 1.96 * sd / np.sqrt(n) if n > 1 else float("nan")
            rows.append({
                "regime": regime,
                "metric": metric,
                "mean": mean,
                "ci95_low": mean - half if n > 1 else float("nan"),
                "ci95_high": mean + half if n > 1 else float("nan"),
                "n": n,
            })
    return pd.DataFrame(rows)
