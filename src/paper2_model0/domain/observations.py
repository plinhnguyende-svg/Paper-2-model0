from dataclasses import dataclass


@dataclass(frozen=True)
class RetailerObservation:
    current_day: int
    current_consumer_demand: float
    on_hand_inventory: float
    usable_pipeline_inventory: float
    previous_forecast: float


@dataclass(frozen=True)
class ImporterReplenishmentObservation:
    current_day: int
    current_retailer_orders: tuple[float, float, float]
    previous_forecast: float
    on_hand_inventory: float
    usable_pipeline_inventory: float


@dataclass(frozen=True)
class ImporterObservation:
    current_day: int
    current_retailer_orders: tuple[float, float, float]
    on_hand_inventory: float
    usable_pipeline_inventory: float
    verified_exporter_availability: tuple[bool | None, bool | None]


@dataclass(frozen=True)
class ExporterObservation:
    current_day: int
    announced_procurement_requirement: float
    own_operational_availability: bool
    rival_operational_availability: bool | None
    own_on_hand_inventory: float
    rival_availability_probability: float
    buyer_uses_verified_state_contingent_allocation: bool
