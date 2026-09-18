from __future__ import annotations

from dataclasses import fields

import numpy as np
import pandas as pd

from paper2_model0.config import SimulationConfig
from paper2_model0.decision_architectures import RuleBasedDecisionArchitecture
from paper2_model0.domain.observations import (
    ExporterObservation,
    ImporterObservation,
    ImporterReplenishmentObservation,
    RetailerObservation,
)
from paper2_model0.domain.scenario import deterministic_scenario
from paper2_model0.engine.model import SupplyChainModel


class RecordingAIStubDecisionArchitecture:
    """Deterministic AI-shaped stub used only to audit the information firewall.

    It delegates decisions to the validated RuleBased adapter so that this test
    introduces no performance treatment. Its only new behavior is recording
    exactly what the engine passes across the policy boundary.
    """

    name = "AI-stub-no-training"

    def __init__(self, config: SimulationConfig):
        self.delegate = RuleBasedDecisionArchitecture(config)
        self.retailer_observations = []
        self.importer_replenishment_observations = []
        self.importer_allocation_calls = []
        self.exporter_observations = []

    def retailer_replenishment(self, observation: RetailerObservation):
        self.retailer_observations.append(observation)
        return self.delegate.retailer_replenishment(observation)

    def importer_replenishment(
        self, observation: ImporterReplenishmentObservation
    ):
        self.importer_replenishment_observations.append(observation)
        return self.delegate.importer_replenishment(observation)

    def importer_allocation(
        self,
        procurement_requirement: float,
        observation: ImporterObservation,
    ):
        self.importer_allocation_calls.append(
            (float(procurement_requirement), observation)
        )
        return self.delegate.importer_allocation(
            procurement_requirement, observation
        )

    def exporter_readiness(self, observation: ExporterObservation):
        self.exporter_observations.append(observation)
        return self.delegate.exporter_readiness(observation)


def _config(T=6):
    return SimulationConfig(
        simulation_horizon_days=T,
        warmup_days=0,
        shelf_life_days=7,
        exporter_to_importer_lead_time_days=2,
        importer_to_retailer_lead_time_days=1,
        retailer_mean_demand=(10.0, 10.0, 10.0),
        demand_forecast_smoothing_weight=0.3,
        exporter_availability_probability=(0.5, 0.5),
    )


def _scenario(T=6):
    demand = np.full((T, 3), 10.0)
    pattern = np.array(
        [[1, 0], [1, 1], [0, 1], [1, 1], [0, 0], [1, 0]],
        dtype=bool,
    )
    availability = np.vstack([pattern[i % len(pattern)] for i in range(T)])
    return deterministic_scenario(demand, availability, seed=20260918)


def _field_names(cls):
    return {f.name for f in fields(cls)}


def test_observation_schema_has_no_raw_model_or_scenario_handles():
    forbidden = {
        "model",
        "scenario",
        "regime",
        "architecture",
        "decision_architecture",
        "exporter_availability",
        "consumer_demand_path",
    }
    for cls in (
        RetailerObservation,
        ImporterReplenishmentObservation,
        ImporterObservation,
        ExporterObservation,
    ):
        assert _field_names(cls).isdisjoint(forbidden)


def test_importer_replenishment_firewall_excludes_current_exporter_state():
    expected = {
        "current_day",
        "current_retailer_orders",
        "previous_forecast",
        "on_hand_inventory",
        "usable_pipeline_inventory",
    }
    assert _field_names(ImporterReplenishmentObservation) == expected


def test_ai_stub_can_substitute_without_changing_rulebased_outputs():
    config = _config()
    scenario = _scenario()

    for regime in ("N", "S", "F"):
        baseline = SupplyChainModel(config, regime, scenario).run()

        recorder = RecordingAIStubDecisionArchitecture(config)
        through_safe_interface = SupplyChainModel(
            config,
            regime,
            scenario,
            decision_architecture=recorder,
        ).run()

        pd.testing.assert_frame_equal(
            baseline,
            through_safe_interface,
            check_dtype=False,
            atol=1e-12,
            rtol=1e-12,
        )


def test_n_s_f_information_rights_are_preserved_at_ai_policy_boundary():
    config = _config(T=1)
    demand = np.full((1, 3), 10.0)
    availability = np.array([[1, 0]], dtype=bool)
    scenario = deterministic_scenario(demand, availability, seed=77)

    records = {}
    for regime in ("N", "S", "F"):
        recorder = RecordingAIStubDecisionArchitecture(config)
        SupplyChainModel(
            config,
            regime,
            scenario,
            decision_architecture=recorder,
        ).run()
        records[regime] = recorder

    # Importer replenishment is formed before current exporter availability is
    # revealed and therefore has the same observation schema in every regime.
    for regime in ("N", "S", "F"):
        imp_rep = records[regime].importer_replenishment_observations[0]
        assert not hasattr(imp_rep, "verified_exporter_availability")
        assert not hasattr(imp_rep, "rival_operational_availability")

    # Allocation boundary: N hides current exporter state; S and F reveal the
    # same verified state to the importer.
    n_imp = records["N"].importer_allocation_calls[0][1]
    s_imp = records["S"].importer_allocation_calls[0][1]
    f_imp = records["F"].importer_allocation_calls[0][1]
    assert n_imp.verified_exporter_availability == (None, None)
    assert s_imp.verified_exporter_availability == (True, False)
    assert f_imp.verified_exporter_availability == (True, False)

    # Exporter boundary: own current availability is always known. Rival
    # current availability is hidden in N and S and visible only in F.
    for regime in ("N", "S", "F"):
        e1 = records[regime].exporter_observations[0]
        assert e1.own_operational_availability is True

    assert records["N"].exporter_observations[0].rival_operational_availability is None
    assert records["S"].exporter_observations[0].rival_operational_availability is None
    assert records["F"].exporter_observations[0].rival_operational_availability is False


def test_ai_boundary_never_receives_the_exogenous_scenario_object():
    config = _config(T=1)
    scenario = _scenario(T=1)
    recorder = RecordingAIStubDecisionArchitecture(config)

    SupplyChainModel(
        config,
        "F",
        scenario,
        decision_architecture=recorder,
    ).run()

    observed_objects = (
        recorder.retailer_observations
        + recorder.importer_replenishment_observations
        + [obs for _, obs in recorder.importer_allocation_calls]
        + recorder.exporter_observations
    )

    assert observed_objects
    for observation in observed_objects:
        assert observation is not scenario
        assert not hasattr(observation, "consumer_demand")
        assert not hasattr(observation, "exporter_availability")
