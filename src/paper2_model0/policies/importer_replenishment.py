from dataclasses import dataclass


@dataclass(frozen=True)
class ImporterReplenishmentAction:
    updated_forecast: float
    procurement_requirement: float


class RuleBasedImporterReplenishmentPolicy:
    def decide(self, *, retailer_orders: tuple[float, float, float], previous_forecast: float,
               on_hand_inventory: float, usable_pipeline_inventory: float,
               alpha: float, lead_time: int) -> ImporterReplenishmentAction:
        aggregate_orders = sum(retailer_orders)
        forecast = alpha * aggregate_orders + (1.0 - alpha) * previous_forecast
        inventory_position = on_hand_inventory + usable_pipeline_inventory
        target = (lead_time + 1) * forecast
        q = max(0.0, target - inventory_position)
        return ImporterReplenishmentAction(forecast, q)
