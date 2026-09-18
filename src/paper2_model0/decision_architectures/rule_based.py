from __future__ import annotations

from paper2_model0.config import SimulationConfig
from paper2_model0.domain.observations import (
    ExporterObservation,
    ImporterObservation,
    ImporterReplenishmentObservation,
    RetailerObservation,
)
from paper2_model0.policies.exporter_readiness import RuleBasedExporterReadinessPolicy
from paper2_model0.policies.importer_allocation import RuleBasedImporterAllocationPolicy
from paper2_model0.policies.importer_replenishment import RuleBasedImporterReplenishmentPolicy
from paper2_model0.policies.retailer_replenishment import RuleBasedRetailerReplenishmentPolicy


class RuleBasedDecisionArchitecture:
    """Observation-safe adapter for the validated RuleBased policy set.

    The validated policies are not re-derived here. This adapter binds static
    configuration once and exposes only typed observations to the engine-facing
    decision interface.
    """

    name = "RuleBased"

    def __init__(self, config: SimulationConfig):
        self.alpha = config.demand_forecast_smoothing_weight
        self.exporter_to_importer_lead_time_days = (
            config.exporter_to_importer_lead_time_days
        )
        self.importer_to_retailer_lead_time_days = (
            config.importer_to_retailer_lead_time_days
        )

        # Public aliases preserve compatibility with the validated benchmark
        # tests while the engine itself now calls the observation-safe methods.
        self.retailer_policy = RuleBasedRetailerReplenishmentPolicy()
        self.importer_replenishment_policy = RuleBasedImporterReplenishmentPolicy()
        self.importer_allocation_policy = RuleBasedImporterAllocationPolicy()
        self.exporter_readiness_policy = RuleBasedExporterReadinessPolicy()

    def retailer_replenishment(self, observation: RetailerObservation):
        return self.retailer_policy.decide(
            observation,
            alpha=self.alpha,
            lead_time=self.importer_to_retailer_lead_time_days,
        )

    def importer_replenishment(
        self, observation: ImporterReplenishmentObservation
    ):
        return self.importer_replenishment_policy.decide(
            retailer_orders=observation.current_retailer_orders,
            previous_forecast=observation.previous_forecast,
            on_hand_inventory=observation.on_hand_inventory,
            usable_pipeline_inventory=observation.usable_pipeline_inventory,
            alpha=self.alpha,
            lead_time=self.exporter_to_importer_lead_time_days,
        )

    def importer_allocation(
        self,
        procurement_requirement: float,
        observation: ImporterObservation,
    ):
        return self.importer_allocation_policy.decide(
            procurement_requirement,
            observation,
        )

    def exporter_readiness(self, observation: ExporterObservation):
        return self.exporter_readiness_policy.decide(observation)
