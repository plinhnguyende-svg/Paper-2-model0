from dataclasses import dataclass
from paper2_model0.domain.observations import RetailerObservation


@dataclass(frozen=True)
class RetailerAction:
    updated_forecast: float
    replenishment_order: float


class RuleBasedRetailerReplenishmentPolicy:
    def decide(self, observation: RetailerObservation, *, alpha: float, lead_time: int) -> RetailerAction:
        forecast = (
            alpha * observation.current_consumer_demand
            + (1.0 - alpha) * observation.previous_forecast
        )
        inventory_position = observation.on_hand_inventory + observation.usable_pipeline_inventory
        target = (lead_time + 1) * forecast
        order = max(0.0, target - inventory_position)
        return RetailerAction(forecast, order)
