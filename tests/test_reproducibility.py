from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import generate_scenario
from paper2_model0.engine.model import SupplyChainModel


def test_common_random_scenario_is_immutable_and_shared():
    config = SimulationConfig(simulation_horizon_days=20, warmup_days=0)
    scenario = generate_scenario(config, 123456)
    assert scenario.consumer_demand.flags.writeable is False
    assert scenario.exporter_availability.flags.writeable is False
    ids = []
    for regime in ["N", "S", "F"]:
        model = SupplyChainModel(config, regime, scenario)
        ids.append(model.scenario.scenario_id)
    assert len(set(ids)) == 1


def test_regime_order_invariance():
    config = SimulationConfig(simulation_horizon_days=30, warmup_days=5)
    scenario = generate_scenario(config, 98765)

    def run_order(order):
        return {r: SupplyChainModel(config, r, scenario).run() for r in order}

    a = run_order(["N", "S", "F"])
    b = run_order(["F", "N", "S"])
    for r in ["N", "S", "F"]:
        assert a[r].equals(b[r])
