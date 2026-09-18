from __future__ import annotations

from dataclasses import dataclass
import math

from paper2_model0.domain.observations import (
    ExporterObservation,
    ImporterReplenishmentObservation,
    RetailerObservation,
)
from paper2_model0.policies.exporter_readiness import ExporterReadinessAction
from paper2_model0.policies.importer_replenishment import ImporterReplenishmentAction
from paper2_model0.policies.retailer_replenishment import RetailerAction
from .forecast import FixedForecastTransitionAdapter


def stable_sigmoid(value: float) -> float:
    """Numerically stable logistic sigmoid for scalar latent actions."""
    z = float(value)
    if math.isnan(z):
        raise ValueError("latent action must not be NaN.")
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


@dataclass(frozen=True)
class BoundedActionTransformer:
    """Map latent AI actions into institutionally feasible Model-0 actions."""

    shelf_life_days: int
    retailer_mean_demand: tuple[float, float, float]
    forecast_transition: FixedForecastTransitionAdapter

    def __post_init__(self) -> None:
        if self.shelf_life_days < 1:
            raise ValueError("shelf_life_days must be at least 1.")
        if len(self.retailer_mean_demand) != 3:
            raise ValueError("AI v0.1 requires exactly three retailer mean demands.")
        if any(float(x) <= 0.0 for x in self.retailer_mean_demand):
            raise ValueError(
                "AI v0.1 bounded targets require strictly positive retailer mean demand."
            )

    @property
    def aggregate_mean_demand(self) -> float:
        return float(sum(self.retailer_mean_demand))

    def retailer_action(
        self,
        latent_action: float,
        observation: RetailerObservation,
        retailer_index: int,
    ) -> RetailerAction:
        if retailer_index not in (0, 1, 2):
            raise IndexError("retailer_index must be 0, 1, or 2.")
        mean_demand = float(self.retailer_mean_demand[retailer_index])
        max_target = float(self.shelf_life_days) * mean_demand
        target = max_target * stable_sigmoid(latent_action)
        inventory_position = (
            observation.on_hand_inventory
            + observation.usable_pipeline_inventory
        )
        order = max(0.0, target - inventory_position)
        updated_forecast = self.forecast_transition.retailer_next_forecast(
            observation
        )
        return RetailerAction(
            updated_forecast=updated_forecast,
            replenishment_order=float(order),
        )

    def importer_replenishment_action(
        self,
        latent_action: float,
        observation: ImporterReplenishmentObservation,
    ) -> ImporterReplenishmentAction:
        max_target = float(self.shelf_life_days) * self.aggregate_mean_demand
        target = max_target * stable_sigmoid(latent_action)
        inventory_position = (
            observation.on_hand_inventory
            + observation.usable_pipeline_inventory
        )
        procurement_requirement = max(0.0, target - inventory_position)
        updated_forecast = self.forecast_transition.importer_next_forecast(
            observation
        )
        return ImporterReplenishmentAction(
            updated_forecast=updated_forecast,
            procurement_requirement=float(procurement_requirement),
        )

    def exporter_readiness_action(
        self,
        latent_action: float,
        observation: ExporterObservation,
    ) -> ExporterReadinessAction:
        if not observation.own_operational_availability:
            return ExporterReadinessAction(0.0, 0.0)

        procurement_requirement = max(
            0.0, float(observation.announced_procurement_requirement)
        )
        target = procurement_requirement * stable_sigmoid(latent_action)
        prepared = max(0.0, target - observation.own_on_hand_inventory)
        return ExporterReadinessAction(
            readiness_target=float(target),
            prepared_quantity=float(prepared),
        )
