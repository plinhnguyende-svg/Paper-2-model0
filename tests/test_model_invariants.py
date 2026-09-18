import numpy as np

from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import deterministic_scenario
from paper2_model0.engine.model import SupplyChainModel


def test_v2_material_conservation_runs_without_failure():
    T = 20
    demand = np.full((T, 3), 10.0)
    availability = np.ones((T, 2), dtype=bool)
    config = SimulationConfig(
        simulation_horizon_days=T,
        warmup_days=0,
        shelf_life_days=7,
        exporter_to_importer_lead_time_days=2,
        importer_to_retailer_lead_time_days=1,
        retailer_mean_demand=(10.0, 10.0, 10.0),
        exporter_availability_probability=(1.0, 1.0),
    )
    scenario = deterministic_scenario(demand, availability)
    model = SupplyChainModel(config, "N", scenario)
    model.run()
    lhs = model.initial_material + model.cumulative_prepared
    rhs = (
        model._on_hand_total()
        + model.shipments.total_in_transit()
        + model.cumulative_consumed
        + model.cumulative_waste
    )
    assert np.isclose(lhs, rhs, atol=1e-7)


def test_v4_zero_demand_zero_initial_forecast_and_stock():
    T = 5
    demand = np.zeros((T, 3))
    availability = np.ones((T, 2), dtype=bool)
    config = SimulationConfig(
        simulation_horizon_days=T,
        warmup_days=0,
        shelf_life_days=5,
        exporter_to_importer_lead_time_days=1,
        importer_to_retailer_lead_time_days=1,
        retailer_mean_demand=(0.0, 0.0, 0.0),
        exporter_availability_probability=(1.0, 1.0),
    )
    scenario = deterministic_scenario(demand, availability)
    df = SupplyChainModel(config, "F", scenario).run()
    assert (df["aggregate_retailer_orders"] == 0).all()
    assert (df["procurement_requirement"] == 0).all()
    assert (df["prepared_quantity_1"] == 0).all()
    assert (df["prepared_quantity_2"] == 0).all()
