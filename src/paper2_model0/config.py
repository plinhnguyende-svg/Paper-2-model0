from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    number_of_retailers: int = 3
    simulation_horizon_days: int = 1000
    warmup_days: int = 200
    shelf_life_days: int = 7
    exporter_to_importer_lead_time_days: int = 2
    importer_to_retailer_lead_time_days: int = 1
    retailer_mean_demand: tuple[float, ...] = (10.0, 10.0, 10.0)
    demand_forecast_smoothing_weight: float = 0.30
    exporter_availability_probability: tuple[float, float] = (0.80, 0.80)

    def validate(self) -> None:
        if self.number_of_retailers != 3:
            raise ValueError("Model 0 is locked to exactly 3 retailers.")
        if len(self.retailer_mean_demand) != self.number_of_retailers:
            raise ValueError("retailer_mean_demand length must match number_of_retailers.")
        if len(self.exporter_availability_probability) != 2:
            raise ValueError("Model 0 is locked to exactly 2 exporters.")
        if self.simulation_horizon_days <= 0:
            raise ValueError("simulation_horizon_days must be positive.")
        if not 0 <= self.warmup_days < self.simulation_horizon_days:
            raise ValueError("warmup_days must satisfy 0 <= warmup < horizon.")
        if self.shelf_life_days < 1:
            raise ValueError("shelf_life_days must be at least 1.")
        if self.exporter_to_importer_lead_time_days < 1:
            raise ValueError("exporter_to_importer_lead_time_days must be at least 1.")
        if self.importer_to_retailer_lead_time_days < 1:
            raise ValueError("importer_to_retailer_lead_time_days must be at least 1.")
        if not 0 < self.demand_forecast_smoothing_weight <= 1:
            raise ValueError("demand_forecast_smoothing_weight must be in (0, 1].")
        if any(x < 0 for x in self.retailer_mean_demand):
            raise ValueError("Retailer mean demand must be nonnegative.")
        if any(not 0 <= p <= 1 for p in self.exporter_availability_probability):
            raise ValueError("Exporter availability probabilities must be in [0, 1].")
