import numpy as np
import pandas as pd

from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import deterministic_scenario
from paper2_model0.engine.model import SupplyChainModel
from paper2_model0.architectures.selective_blockchain import SelectiveBlockchainArchitecture


COMPARE_COLS = [
    "aggregate_consumer_demand",
    "aggregate_fulfilled_consumer_demand",
    "aggregate_retailer_orders",
    "procurement_requirement",
    "readiness_target_1",
    "readiness_target_2",
    "prepared_quantity_1",
    "prepared_quantity_2",
    "allocation_1",
    "allocation_2",
    "upstream_shipment_1",
    "upstream_shipment_2",
    "total_on_hand_inventory",
    "total_pipeline_inventory",
    "total_waste",
]


def base_config(T=30, p=(1.0, 1.0)):
    return SimulationConfig(
        simulation_horizon_days=T,
        warmup_days=0,
        shelf_life_days=7,
        exporter_to_importer_lead_time_days=2,
        importer_to_retailer_lead_time_days=1,
        retailer_mean_demand=(10.0, 11.0, 9.0),
        demand_forecast_smoothing_weight=0.3,
        exporter_availability_probability=p,
    )


def test_v5_perfect_availability_neutrality_n_s_f():
    T = 30
    rng = np.random.default_rng(123)
    demand = rng.poisson([10.0, 11.0, 9.0], size=(T, 3)).astype(float)
    availability = np.ones((T, 2), dtype=bool)
    scenario = deterministic_scenario(demand, availability)
    config = base_config(T, (1.0, 1.0))

    frames = {r: SupplyChainModel(config, r, scenario).run() for r in ["N", "S", "F"]}
    pd.testing.assert_frame_equal(frames["N"][COMPARE_COLS], frames["S"][COMPARE_COLS], check_dtype=False, atol=1e-10, rtol=1e-10)
    pd.testing.assert_frame_equal(frames["S"][COMPARE_COLS], frames["F"][COMPARE_COLS], check_dtype=False, atol=1e-10, rtol=1e-10)


def test_v6_hiding_rival_from_f_collapses_to_s():
    T = 20
    demand = np.full((T, 3), 10.0)
    availability = np.array([[1, 0], [1, 1], [0, 1], [1, 1], [0, 0]] * 4, dtype=bool)
    scenario = deterministic_scenario(demand, availability)
    config = base_config(T, (0.5, 0.5))

    s_df = SupplyChainModel(config, "S", scenario).run()
    # Inject S observation rules into a run labelled F. Physical model remains unchanged.
    f_hidden_df = SupplyChainModel(config, "F", scenario, architecture=SelectiveBlockchainArchitecture()).run()
    pd.testing.assert_frame_equal(s_df[COMPARE_COLS], f_hidden_df[COMPARE_COLS], check_dtype=False, atol=1e-10, rtol=1e-10)


def test_v7_vertical_verification_isolation_allocation():
    T = 1
    demand = np.zeros((T, 3))
    availability = np.array([[1, 0]], dtype=bool)
    config = SimulationConfig(
        simulation_horizon_days=T,
        warmup_days=0,
        shelf_life_days=10,
        exporter_to_importer_lead_time_days=1,
        importer_to_retailer_lead_time_days=1,
        retailer_mean_demand=(10.0, 10.0, 10.0),
        exporter_availability_probability=(0.5, 0.5),
    )
    scenario = deterministic_scenario(demand, availability)

    n = SupplyChainModel(config, "N", scenario)
    s = SupplyChainModel(config, "S", scenario)
    # Force a clean one-period procurement requirement by clearing importer and setting forecast.
    for model in (n, s):
        model.importer.inventory.age_buckets[:] = 0.0
        model.importer.downstream_order_forecast = 100.0 / 2.0  # with lead_time 1 => Q=100 when no retailer orders after update only if alpha=0; instead direct policy below

    # Test the allocation policy itself with legal observations and Q=100.
    n_obs = n.architecture.importer_observation(day=0, retailer_orders=(0, 0, 0), on_hand_inventory=0, usable_pipeline_inventory=0, availability=(True, False))
    s_obs = s.architecture.importer_observation(day=0, retailer_orders=(0, 0, 0), on_hand_inventory=0, usable_pipeline_inventory=0, availability=(True, False))
    assert n.importer_allocation_policy.decide(100.0, n_obs) == (50.0, 50.0)
    assert s.importer_allocation_policy.decide(100.0, s_obs) == (100.0, 0.0)
