from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from paper2_model0.config import SimulationConfig
from paper2_model0.validation import (
    ofat_diagnostic,
    phase_map_diagnostic,
    replication_sufficiency_diagnostic,
    seed_stability_diagnostic,
    warmup_convergence_diagnostic,
)


def _tupleize_config(raw: dict) -> dict:
    raw = dict(raw)
    raw["retailer_mean_demand"] = tuple(raw["retailer_mean_demand"])
    raw["exporter_availability_probability"] = tuple(
        raw["exporter_availability_probability"]
    )
    return raw


def _load_spec(path: str):
    with open(path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    config = SimulationConfig(**_tupleize_config(spec["base_config"]))
    return spec, config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=["warmup", "replications", "seeds", "ofat", "ofat_all", "phase", "phase_all"],
    )
    parser.add_argument(
        "--config",
        default="experiments/validation_protocol_v0.1.yaml",
    )
    parser.add_argument(
        "--output",
        default="outputs/validation_protocol_v0.1",
    )
    parser.add_argument("--factor", default=None)
    parser.add_argument("--map-index", type=int, default=0)
    args = parser.parse_args()

    spec, base_config = _load_spec(args.config)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    if args.stage == "warmup":
        s = spec["warmup"]
        df = warmup_convergence_diagnostic(
            base_config,
            warmup_candidates_days=s["warmup_candidates_days"],
            measurement_window_days=int(s["measurement_window_days"]),
            number_of_replications=int(s["number_of_replications"]),
            master_seed=int(s["master_seed"]),
        )
        path = out / "warmup_convergence.csv"

    elif args.stage == "replications":
        s = spec["replication_sufficiency"]
        df = replication_sufficiency_diagnostic(
            base_config,
            max_replications=int(s["max_replications"]),
            checkpoints=s["checkpoints"],
            master_seed=int(s["master_seed"]),
        )
        path = out / "replication_sufficiency.csv"

    elif args.stage == "seeds":
        s = spec["seed_stability"]
        df = seed_stability_diagnostic(
            base_config,
            master_seeds=s["master_seeds"],
            number_of_replications=int(s["number_of_replications"]),
        )
        path = out / "seed_stability.csv"

    elif args.stage in {"ofat", "ofat_all"}:
        s = spec["ofat"]
        if args.stage == "ofat":
            if args.factor is None:
                raise SystemExit(
                    "--factor is required for the ofat stage; choose one key under ofat.factors"
                )
            if args.factor not in s["factors"]:
                raise SystemExit(f"Unknown OFAT factor: {args.factor}")
            df = ofat_diagnostic(
                base_config,
                factor_name=args.factor,
                values=s["factors"][args.factor],
                number_of_replications=int(s["number_of_replications"]),
                master_seed=int(s["master_seed"]),
            )
            safe = args.factor.replace("/", "_")
            path = out / f"ofat_{safe}.csv"
        else:
            frames = []
            for factor_name, values in s["factors"].items():
                frames.append(
                    ofat_diagnostic(
                        base_config,
                        factor_name=factor_name,
                        values=values,
                        number_of_replications=int(s["number_of_replications"]),
                        master_seed=int(s["master_seed"]),
                    )
                )
            import pandas as pd
            df = pd.concat(frames, ignore_index=True)
            path = out / "ofat_all.csv"

    else:
        s = spec["phase_maps"]
        maps = s["maps"]
        if args.stage == "phase":
            if not 0 <= args.map_index < len(maps):
                raise SystemExit("--map-index is outside the configured phase-map list")
            selected_maps = [(args.map_index, maps[args.map_index])]
        else:
            selected_maps = list(enumerate(maps))

        frames = []
        for map_index, m in selected_maps:
            tmp = phase_map_diagnostic(
                base_config,
                x_name=m["x_name"],
                x_values=m["x_values"],
                y_name=m["y_name"],
                y_values=m["y_values"],
                number_of_replications=int(s["number_of_replications"]),
                master_seed=int(s["master_seed"]),
            )
            tmp.insert(0, "map_index", map_index)
            frames.append(tmp)

        import pandas as pd
        df = pd.concat(frames, ignore_index=True)
        path = (
            out / f"phase_map_{args.map_index}.csv"
            if args.stage == "phase"
            else out / "phase_maps_all.csv"
        )

    df.to_csv(path, index=False)
    print(f"Wrote {len(df)} rows to {path}")


if __name__ == "__main__":
    main()
