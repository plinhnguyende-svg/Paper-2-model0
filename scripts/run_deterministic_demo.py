import numpy as np
import pandas as pd

from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import deterministic_scenario
from paper2_model0.engine.model import SupplyChainModel


def main():
    demand = np.full((10, 3), 10.0)
    availability = np.array([
        [1, 1], [1, 0], [1, 1], [0, 1], [0, 0],
        [1, 0], [1, 1], [0, 1], [1, 1], [1, 0],
    ], dtype=bool)
    config = SimulationConfig(
        simulation_horizon_days=10,
        warmup_days=0,
        shelf_life_days=5,
        exporter_to_importer_lead_time_days=1,
        importer_to_retailer_lead_time_days=1,
        retailer_mean_demand=(10.0, 10.0, 10.0),
        demand_forecast_smoothing_weight=0.30,
        exporter_availability_probability=(0.5, 0.5),
    )
    scenario = deterministic_scenario(demand, availability)
    frames = []
    for regime in ["N", "S", "F"]:
        df = SupplyChainModel(config, regime, scenario).run()
        cols = [
            "day", "regime", "procurement_requirement",
            "availability_1", "availability_2",
            "readiness_target_1", "readiness_target_2",
            "prepared_quantity_1", "prepared_quantity_2",
            "allocation_1", "allocation_2",
            "upstream_shipment_1", "upstream_shipment_2",
        ]
        frames.append(df[cols])
    out = pd.concat(frames, ignore_index=True)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
