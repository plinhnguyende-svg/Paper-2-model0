from __future__ import annotations

from dataclasses import dataclass
import hashlib
import numpy as np

from paper2_model0.config import SimulationConfig


@dataclass(frozen=True)
class ExogenousScenario:
    consumer_demand: np.ndarray  # shape T x 3
    exporter_availability: np.ndarray  # shape T x 2, bool
    replication_seed: int
    scenario_id: str


def _scenario_id(demand: np.ndarray, availability: np.ndarray, seed: int) -> str:
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(demand).tobytes())
    h.update(np.ascontiguousarray(availability).tobytes())
    h.update(str(seed).encode())
    return h.hexdigest()[:16]


def generate_scenario(config: SimulationConfig, replication_seed: int) -> ExogenousScenario:
    """Generate independent named streams once, before any regime is run."""
    config.validate()
    seed_sequence = np.random.SeedSequence(replication_seed)
    children = seed_sequence.spawn(5)

    demand = np.empty((config.simulation_horizon_days, 3), dtype=float)
    for r in range(3):
        rng = np.random.default_rng(children[r])
        demand[:, r] = rng.poisson(
            lam=config.retailer_mean_demand[r],
            size=config.simulation_horizon_days,
        ).astype(float)

    availability = np.empty((config.simulation_horizon_days, 2), dtype=bool)
    for i in range(2):
        rng = np.random.default_rng(children[3 + i])
        availability[:, i] = (
            rng.random(config.simulation_horizon_days)
            < config.exporter_availability_probability[i]
        )

    demand.setflags(write=False)
    availability.setflags(write=False)
    sid = _scenario_id(demand, availability, replication_seed)
    return ExogenousScenario(demand, availability, replication_seed, sid)


def deterministic_scenario(
    consumer_demand: np.ndarray,
    exporter_availability: np.ndarray,
    seed: int = 0,
) -> ExogenousScenario:
    demand = np.asarray(consumer_demand, dtype=float).copy()
    availability = np.asarray(exporter_availability, dtype=bool).copy()
    if demand.ndim != 2 or demand.shape[1] != 3:
        raise ValueError("consumer_demand must have shape T x 3")
    if availability.shape != (demand.shape[0], 2):
        raise ValueError("exporter_availability must have shape T x 2")
    demand.setflags(write=False)
    availability.setflags(write=False)
    sid = _scenario_id(demand, availability, seed)
    return ExogenousScenario(demand, availability, seed, sid)
