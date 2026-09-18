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
from .base import validate_decision_architecture


class BoundRuleBasedRetailerPolicy:
    def __init__(self, *, alpha: float, lead_time: int):
        self.alpha = float(alpha)
        self.lead_time = int(lead_time)
        self.policy = RuleBasedRetailerReplenishmentPolicy()

    def decide(self, observation: RetailerObservation):
        return self.policy.decide(
            observation,
            alpha=self.alpha,
            lead_time=self.lead_time,
        )


class BoundRuleBasedImporterPolicy:
    def __init__(self, *, alpha: float, lead_time: int):
        self.alpha = float(alpha)
        self.lead_time = int(lead_time)
        self.replenishment_policy = RuleBasedImporterReplenishmentPolicy()
        self.allocation_policy = RuleBasedImporterAllocationPolicy()

    def decide_replenishment(
        self, observation: ImporterReplenishmentObservation
    ):
        return self.replenishment_policy.decide(
            retailer_orders=observation.current_retailer_orders,
            previous_forecast=observation.previous_forecast,
            on_hand_inventory=observation.on_hand_inventory,
            usable_pipeline_inventory=observation.usable_pipeline_inventory,
            alpha=self.alpha,
            lead_time=self.lead_time,
        )

    def decide_allocation(
        self,
        procurement_requirement: float,
        observation: ImporterObservation,
    ):
        return self.allocation_policy.decide(
            procurement_requirement,
            observation,
        )


class BoundRuleBasedExporterPolicy:
    def __init__(self):
        self.policy = RuleBasedExporterReadinessPolicy()

    def decide(self, observation: ExporterObservation):
        return self.policy.decide(observation)


class RuleBasedDecisionArchitecture:
    """Actor-isolated adapter for the validated RuleBased policy set."""

    name = "RuleBased"

    def __init__(self, config: SimulationConfig):
        self.retailer_policies = tuple(
            BoundRuleBasedRetailerPolicy(
                alpha=config.demand_forecast_smoothing_weight,
                lead_time=config.importer_to_retailer_lead_time_days,
            )
            for _ in range(3)
        )
        self.importer_policy = BoundRuleBasedImporterPolicy(
            alpha=config.demand_forecast_smoothing_weight,
            lead_time=config.exporter_to_importer_lead_time_days,
        )
        self.exporter_policies = (
            BoundRuleBasedExporterPolicy(),
            BoundRuleBasedExporterPolicy(),
        )

        validate_decision_architecture(self)

        # Compatibility aliases preserve the frozen benchmark's direct policy
        # tests. The simulation engine does not use these aliases for routing.
        self.retailer_policy = self.retailer_policies[0].policy
        self.importer_replenishment_policy = (
            self.importer_policy.replenishment_policy
        )
        self.importer_allocation_policy = self.importer_policy.allocation_policy
        self.exporter_readiness_policy = self.exporter_policies[0].policy
