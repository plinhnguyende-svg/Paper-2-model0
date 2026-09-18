from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Shipment:
    origin_id: str
    destination_id: str
    quantity: float
    age_at_dispatch: int
    dispatch_day: int
    arrival_day: int

    def age_at_arrival(self) -> int:
        return self.age_at_dispatch + (self.arrival_day - self.dispatch_day)


class ShipmentManager:
    def __init__(self):
        self._shipments: list[Shipment] = []

    def schedule(self, shipment: Shipment) -> None:
        if shipment.quantity < 0:
            raise ValueError("Shipment quantity must be nonnegative.")
        if shipment.arrival_day <= shipment.dispatch_day:
            raise ValueError("Arrival day must be after dispatch day.")
        if shipment.quantity > 0:
            self._shipments.append(shipment)

    def arrivals_for_day(self, day: int) -> list[Shipment]:
        due = [s for s in self._shipments if s.arrival_day == day]
        self._shipments = [s for s in self._shipments if s.arrival_day != day]
        return due

    def total_in_transit(self) -> float:
        return float(sum(s.quantity for s in self._shipments))

    def usable_pipeline_quantity(self, destination_id: str, shelf_life_days: int) -> float:
        return float(sum(
            s.quantity
            for s in self._shipments
            if s.destination_id == destination_id and s.age_at_arrival() < shelf_life_days
        ))

    @property
    def shipments(self) -> tuple[Shipment, ...]:
        return tuple(self._shipments)
