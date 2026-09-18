from __future__ import annotations

from dataclasses import dataclass

from paper2_model0.domain.observations import (
    ImporterReplenishmentObservation,
    RetailerObservation,
)


@dataclass(frozen=True)
class FixedForecastTransitionAdapter:
    """Frozen Model-0 exponential-smoothing forecast transition.

    AI v0.1 may choose operational targets, but it does not choose or modify
    the forecast-state law.
    """

    alpha: float

    def __post_init__(self) -> None:
        if not 0.0 < self.alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1].")

    def retailer_next_forecast(self, observation: RetailerObservation) -> float:
        return float(
            self.alpha * observation.current_consumer_demand
            + (1.0 - self.alpha) * observation.previous_forecast
        )

    def importer_next_forecast(
        self,
        observation: ImporterReplenishmentObservation,
    ) -> float:
        aggregate_orders = float(sum(observation.current_retailer_orders))
        return float(
            self.alpha * aggregate_orders
            + (1.0 - self.alpha) * observation.previous_forecast
        )
