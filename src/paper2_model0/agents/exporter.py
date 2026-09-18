from dataclasses import dataclass
from paper2_model0.domain.inventory import PerishableInventory


@dataclass
class Exporter:
    exporter_id: str
    inventory: PerishableInventory
    own_availability_probability: float
    known_rival_availability_probability: float
    cumulative_prepared_quantity: float = 0.0
    cumulative_shipments: float = 0.0
    cumulative_waste: float = 0.0

    def prepare_fresh_units(self, quantity: float) -> None:
        if quantity < 0:
            raise ValueError("Prepared quantity cannot be negative.")
        self.inventory.add(quantity, age=0)
        self.cumulative_prepared_quantity += quantity

    def age_inventory(self) -> float:
        waste = self.inventory.age_one_day()
        self.cumulative_waste += waste
        return waste
