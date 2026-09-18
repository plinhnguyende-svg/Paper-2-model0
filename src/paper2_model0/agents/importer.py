from dataclasses import dataclass
from paper2_model0.domain.inventory import PerishableInventory


@dataclass
class Importer:
    importer_id: str
    inventory: PerishableInventory
    downstream_order_forecast: float
    cumulative_waste: float = 0.0

    def age_inventory(self) -> float:
        waste = self.inventory.age_one_day()
        self.cumulative_waste += waste
        return waste
