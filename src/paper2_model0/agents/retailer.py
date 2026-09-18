from dataclasses import dataclass
from paper2_model0.domain.inventory import PerishableInventory


@dataclass
class Retailer:
    retailer_id: str
    inventory: PerishableInventory
    demand_forecast: float
    cumulative_consumer_demand: float = 0.0
    cumulative_fulfilled_demand: float = 0.0
    cumulative_lost_sales: float = 0.0
    cumulative_waste: float = 0.0

    def serve_consumer_demand(self, demand: float) -> tuple[float, float]:
        lots, unfulfilled = self.inventory.remove_fefo(demand)
        fulfilled = sum(x.quantity for x in lots)
        self.cumulative_consumer_demand += demand
        self.cumulative_fulfilled_demand += fulfilled
        self.cumulative_lost_sales += unfulfilled
        return fulfilled, unfulfilled

    def age_inventory(self) -> float:
        waste = self.inventory.age_one_day()
        self.cumulative_waste += waste
        return waste
