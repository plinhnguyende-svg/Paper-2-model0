from __future__ import annotations

from typing import Protocol
from paper2_model0.domain.observations import ImporterObservation, ExporterObservation


class InformationArchitecture(Protocol):
    name: str

    def importer_observation(
        self,
        *,
        day: int,
        retailer_orders: tuple[float, float, float],
        on_hand_inventory: float,
        usable_pipeline_inventory: float,
        availability: tuple[bool, bool],
    ) -> ImporterObservation: ...

    def exporter_observation(
        self,
        *,
        day: int,
        exporter_index: int,
        procurement_requirement: float,
        on_hand_inventory: float,
        availability: tuple[bool, bool],
        rival_availability_probability: float,
    ) -> ExporterObservation: ...
