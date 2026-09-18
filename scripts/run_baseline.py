from pathlib import Path
import argparse
import yaml

from paper2_model0.config import SimulationConfig
from paper2_model0.experiments.runner import run_paired_experiment, summarize_regimes


def tupleize_config(raw: dict) -> dict:
    raw = dict(raw)
    raw["retailer_mean_demand"] = tuple(raw["retailer_mean_demand"])
    raw["exporter_availability_probability"] = tuple(raw["exporter_availability_probability"])
    return raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiments/baseline.yaml")
    parser.add_argument("--output", default="outputs/baseline")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    config = SimulationConfig(**tupleize_config(spec["config"]))
    replication_df, _ = run_paired_experiment(
        config,
        number_of_replications=int(spec["number_of_replications"]),
        master_seed=int(spec["master_seed"]),
        output_dir=args.output,
    )
    summary = summarize_regimes(replication_df)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output / "regime_summary.csv", index=False)

    selected = summary[summary["metric"].isin([
        "service_level", "waste_share_of_terminal_outflow", "retail_order_bullwhip",
        "importer_procurement_bullwhip", "mean_abs_target_allocation_gap_1",
        "mean_abs_stock_allocation_gap_1",
    ])]
    print(selected.pivot(index="metric", columns="regime", values="mean").round(4))


if __name__ == "__main__":
    main()
