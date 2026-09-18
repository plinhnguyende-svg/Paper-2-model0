from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from paper2_model0.config import SimulationConfig
from paper2_model0.domain.observations import (
    ExporterObservation,
    ImporterReplenishmentObservation,
    RetailerObservation,
)


@dataclass(frozen=True)
class AIObservationEncoder:
    """Deterministic, regime-safe observation encoder for AI policies.

    Only fields already present in the actor's typed observation are encoded.
    No regime label, current day, model handle, or scenario handle is accepted.
    """

    retailer_mean_demand: tuple[float, float, float]

    @classmethod
    def from_config(cls, config: SimulationConfig) -> "AIObservationEncoder":
        means = tuple(float(x) for x in config.retailer_mean_demand)
        if len(means) != 3:
            raise ValueError("AI v0.1 requires exactly three retailer demand scales.")
        if any(x <= 0.0 for x in means):
            raise ValueError(
                "AI v0.1 observation normalization requires strictly positive "
                "retailer mean demand."
            )
        return cls(means)  # type: ignore[arg-type]

    @property
    def aggregate_mean_demand(self) -> float:
        return float(sum(self.retailer_mean_demand))

    def encode_retailer(
        self,
        observation: RetailerObservation,
        retailer_index: int,
    ) -> np.ndarray:
        lam = self._retailer_scale(retailer_index)
        return np.asarray(
            [
                observation.current_consumer_demand / lam,
                observation.on_hand_inventory / lam,
                observation.usable_pipeline_inventory / lam,
                observation.previous_forecast / lam,
            ],
            dtype=np.float64,
        )

    def encode_importer_replenishment(
        self,
        observation: ImporterReplenishmentObservation,
    ) -> np.ndarray:
        l1, l2, l3 = self.retailer_mean_demand
        agg = self.aggregate_mean_demand
        o1, o2, o3 = observation.current_retailer_orders
        return np.asarray(
            [
                o1 / l1,
                o2 / l2,
                o3 / l3,
                observation.previous_forecast / agg,
                observation.on_hand_inventory / agg,
                observation.usable_pipeline_inventory / agg,
            ],
            dtype=np.float64,
        )

    def encode_exporter(
        self,
        observation: ExporterObservation,
    ) -> np.ndarray:
        agg = self.aggregate_mean_demand
        rival = observation.rival_operational_availability
        rival_known = 0.0 if rival is None else 1.0
        rival_value = 0.0 if rival is None else float(bool(rival))
        return np.asarray(
            [
                observation.announced_procurement_requirement / agg,
                float(bool(observation.own_operational_availability)),
                observation.own_on_hand_inventory / agg,
                float(observation.rival_availability_probability),
                float(bool(observation.buyer_uses_verified_state_contingent_allocation)),
                rival_known,
                rival_value,
            ],
            dtype=np.float64,
        )

    def _retailer_scale(self, retailer_index: int) -> float:
        if retailer_index not in (0, 1, 2):
            raise IndexError("retailer_index must be 0, 1, or 2.")
        return self.retailer_mean_demand[retailer_index]
