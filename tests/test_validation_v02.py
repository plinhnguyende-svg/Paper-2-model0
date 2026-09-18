import numpy as np
import pandas as pd

from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import deterministic_scenario
from paper2_model0.domain.shipment import Shipment
from paper2_model0.engine.model import SupplyChainModel
from paper2_model0.experiments.metrics import replication_metrics
from paper2_model0.experiments.runner import run_paired_experiment
from paper2_model0.architectures import build_architecture
from paper2_model0.policies.exporter_readiness import RuleBasedExporterReadinessPolicy


def test_procurement_requirement_is_formed_before_current_availability_is_used():
    T = 2
    demand = np.full((T, 3), 10.0)
    config = SimulationConfig(
        simulation_horizon_days=T,
        warmup_days=0,
        shelf_life_days=7,
        exporter_to_importer_lead_time_days=1,
        importer_to_retailer_lead_time_days=1,
        retailer_mean_demand=(10.0, 10.0, 10.0),
        exporter_availability_probability=(0.5, 0.5),
    )
    s1 = deterministic_scenario(demand, np.array([[1, 1], [1, 1]], dtype=bool), seed=1)
    s2 = deterministic_scenario(demand, np.array([[0, 0], [1, 1]], dtype=bool), seed=2)

    q1 = SupplyChainModel(config, "S", s1).run().loc[0, "procurement_requirement"]
    q2 = SupplyChainModel(config, "S", s2).run().loc[0, "procurement_requirement"]
    assert q1 == q2


def test_importer_shortage_is_rationed_proportionally_not_by_retailer_order():
    config = SimulationConfig(
        simulation_horizon_days=1,
        warmup_days=0,
        shelf_life_days=7,
        exporter_to_importer_lead_time_days=1,
        importer_to_retailer_lead_time_days=1,
    )
    scenario = deterministic_scenario(
        np.zeros((1, 3)),
        np.ones((1, 2), dtype=bool),
    )
    model = SupplyChainModel(config, "N", scenario)
    model.importer.inventory.age_buckets[:] = 0.0
    model.importer.inventory.add(30.0, age=0)

    shipped = model._dispatch_importer_to_retailers((10.0, 20.0, 30.0), day=0)
    assert np.allclose(shipped, (5.0, 10.0, 15.0))


def test_in_transit_expiration_is_recorded_as_waste():
    config = SimulationConfig(
        simulation_horizon_days=2,
        warmup_days=0,
        shelf_life_days=2,
        exporter_to_importer_lead_time_days=1,
        importer_to_retailer_lead_time_days=1,
    )
    scenario = deterministic_scenario(
        np.zeros((2, 3)),
        np.ones((2, 2), dtype=bool),
    )
    model = SupplyChainModel(config, "N", scenario)
    model.shipments.schedule(
        Shipment("E1", "B", 7.0, age_at_dispatch=1, dispatch_day=0, arrival_day=1)
    )

    waste = model._receive_due_shipments(day=1)
    assert waste == 7.0


def test_selective_readiness_uses_the_rivals_probability_under_asymmetry():
    policy = RuleBasedExporterReadinessPolicy()
    architecture = build_architecture("S")
    availability = (True, True)

    e1 = architecture.exporter_observation(
        day=0,
        exporter_index=0,
        procurement_requirement=100.0,
        on_hand_inventory=0.0,
        availability=availability,
        rival_availability_probability=0.2,
    )
    e2 = architecture.exporter_observation(
        day=0,
        exporter_index=1,
        procurement_requirement=100.0,
        on_hand_inventory=0.0,
        availability=availability,
        rival_availability_probability=0.8,
    )

    assert policy.decide(e1).readiness_target == 90.0
    assert policy.decide(e2).readiness_target == 60.0


def test_selective_readiness_probability_boundaries():
    policy = RuleBasedExporterReadinessPolicy()
    architecture = build_architecture("S")
    availability = (True, True)

    p0 = architecture.exporter_observation(
        day=0, exporter_index=0, procurement_requirement=100.0,
        on_hand_inventory=0.0, availability=availability,
        rival_availability_probability=0.0,
    )
    p1 = architecture.exporter_observation(
        day=0, exporter_index=0, procurement_requirement=100.0,
        on_hand_inventory=0.0, availability=availability,
        rival_availability_probability=1.0,
    )
    assert policy.decide(p0).readiness_target == 100.0
    assert policy.decide(p1).readiness_target == 50.0


def test_full_visibility_target_allocation_gap_is_zero():
    T = 8
    demand = np.full((T, 3), 10.0)
    availability = np.array(
        [[1, 1], [1, 0], [0, 1], [0, 0], [1, 0], [1, 1], [0, 1], [1, 1]],
        dtype=bool,
    )
    config = SimulationConfig(
        simulation_horizon_days=T,
        warmup_days=0,
        shelf_life_days=7,
        exporter_to_importer_lead_time_days=1,
        importer_to_retailer_lead_time_days=1,
        retailer_mean_demand=(10.0, 10.0, 10.0),
        exporter_availability_probability=(0.5, 0.5),
    )
    df = SupplyChainModel(
        config, "F", deterministic_scenario(demand, availability)
    ).run()

    assert np.allclose(df["target_allocation_gap_1"], 0.0)
    assert np.allclose(df["target_allocation_gap_2"], 0.0)


def test_clean_waste_metric_uses_only_terminal_outflows_inside_measurement_window():
    df = pd.DataFrame(
        {
            "day": [0, 1, 2, 3],
            "aggregate_consumer_demand": [10.0, 10.0, 10.0, 10.0],
            "aggregate_fulfilled_consumer_demand": [8.0, 8.0, 9.0, 9.0],
            "aggregate_retailer_orders": [10.0, 10.0, 10.0, 10.0],
            "procurement_requirement": [10.0, 10.0, 10.0, 10.0],
            "allocation_1": [5.0] * 4,
            "allocation_2": [5.0] * 4,
            "prepared_quantity_1": [100.0, 100.0, 5.0, 5.0],
            "prepared_quantity_2": [100.0, 100.0, 5.0, 5.0],
            "total_on_hand_inventory": [0.0] * 4,
            "aggregate_lost_sales": [2.0, 2.0, 1.0, 1.0],
            "total_waste": [50.0, 50.0, 1.0, 3.0],
            "abs_target_allocation_gap_1": [0.0] * 4,
            "abs_target_allocation_gap_2": [0.0] * 4,
            "abs_stock_allocation_gap_1": [0.0] * 4,
            "abs_stock_allocation_gap_2": [0.0] * 4,
        }
    )

    metrics = replication_metrics(df, warmup_days=2)
    assert np.isclose(metrics["waste_share_of_terminal_outflow"], 4.0 / (18.0 + 4.0))


def test_paired_runner_reuses_scenario_within_each_replication():
    config = SimulationConfig(
        simulation_horizon_days=8,
        warmup_days=2,
        shelf_life_days=5,
        exporter_to_importer_lead_time_days=1,
        importer_to_retailer_lead_time_days=1,
    )
    replication_df, paired_df = run_paired_experiment(
        config,
        number_of_replications=2,
        master_seed=12345,
    )

    for _, group in replication_df.groupby("replication_id"):
        assert group["scenario_id"].nunique() == 1
        assert set(group["regime"]) == {"N", "S", "F"}

    assert not paired_df.empty
    assert {"S_minus_N", "F_minus_S", "F_minus_N"}.issubset(paired_df.columns)
