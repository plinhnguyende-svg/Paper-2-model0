from __future__ import annotations

import json
from pathlib import Path

from paper2_model0.ai import (
    run_tiny_smoke_training,
    tiny_deterministic_smoke_case,
)


def main() -> None:
    config, scenario = tiny_deterministic_smoke_case()
    results = [
        run_tiny_smoke_training(
            regime=regime,
            config=config,
            scenario=scenario,
            training_seed=41001,
        ).to_dict()
        for regime in ("N", "S", "F")
    ]

    payload = {
        "purpose": "software_smoke_only_not_scientific_training",
        "scenario_id": scenario.scenario_id,
        "horizon_days": config.simulation_horizon_days,
        "training_seed": 41001,
        "regimes": results,
    }

    output = Path("outputs/ai_smoke_v0.1/smoke_summary.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(output)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
