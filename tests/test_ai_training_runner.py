from __future__ import annotations

import math

import numpy as np
import pandas.testing as pdt
import pytest

from paper2_model0.ai import (
    ACTOR_NAMES,
    BoundaryAwareEpisodeRunner,
    PPOUpdateStats,
    expected_rollout_partition,
    physical_team_rewards,
    tiny_deterministic_smoke_case,
)
from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import deterministic_scenario
from paper2_model0.engine.model import SupplyChainModel


def _small_case(horizon: int = 12):
    config = SimulationConfig(
        simulation_horizon_days=horizon,
        warmup_days=0,
        shelf_life_days=4,
        exporter_to_importer_lead_time_days=1,
        importer_to_retailer_lead_time_days=1,
        retailer_mean_demand=(10.0, 10.0, 10.0),
        demand_forecast_smoothing_weight=0.30,
        exporter_availability_probability=(0.80, 0.80),
    )
    demand = np.asarray(
        [[10 + (t % 3), 9 + (t % 2), 11 - (t % 2)] for t in range(horizon)],
        dtype=float,
    )
    availability = np.asarray(
        [[(t % 4) != 2, (t % 5) != 3] for t in range(horizon)],
        dtype=bool,
    )
    return config, deterministic_scenario(demand, availability, seed=812001)


def _zero_stats() -> PPOUpdateStats:
    return PPOUpdateStats(
        policy_loss=0.0,
        value_loss=0.0,
        entropy=0.0,
        total_loss=0.0,
        approximate_kl=0.0,
        clip_fraction=0.0,
        gradient_norm=0.0,
        minibatch_updates=1,
    )


def test_locked_1000_day_partition_is_exact():
    assert expected_rollout_partition(1000, 256) == (256, 256, 256, 232)
    assert sum(expected_rollout_partition(1000, 256)) == 1000


def test_decision_boundary_refactor_preserves_rulebased_trajectory():
    config, scenario = _small_case(12)

    for regime in ("N", "S", "F"):
        ordinary = SupplyChainModel(config, regime, scenario).run()

        stepped_model = SupplyChainModel(config, regime, scenario)
        for day in range(config.simulation_horizon_days):
            boundary = stepped_model.open_decision_boundary(day)
            assert boundary.day == day
            stepped_model.complete_decision_boundary(boundary)
        stepped = stepped_model.recorder.dataframe()

        pdt.assert_frame_equal(ordinary, stepped, check_exact=True)


def test_decision_boundary_cannot_be_opened_twice():
    config, scenario = _small_case(2)
    model = SupplyChainModel(config, "N", scenario)
    model.open_decision_boundary(0)
    with pytest.raises(RuntimeError, match="cannot open"):
        model.open_decision_boundary(1)


def test_previous_transition_reward_is_finalized_only_after_next_preaction_boundary():
    config, scenario = _small_case(2)
    runner = BoundaryAwareEpisodeRunner(
        config=config,
        regime="F",
        scenario=scenario,
        training_seed=41001,
        allow_test_fixture=True,
    )

    b0 = runner.model.open_decision_boundary(0)
    runner._current_boundary_day = 0
    row0 = runner.model.complete_decision_boundary(b0)
    runner._last_completed_row = row0

    assert all(len(buffer) == 0 for buffer in runner.buffers.values())

    b1 = runner.model.open_decision_boundary(1)
    runner._current_boundary_day = 1
    runner._finalize_previous_at_boundary(b1)

    expected = -(
        row0["on_hand_waste"] + b1.transit_waste + sum(b1.lost)
    ) / sum(config.retailer_mean_demand)

    for buffer in runner.buffers.values():
        assert len(buffer) == 1
        assert buffer.rewards == pytest.approx([expected])
        assert buffer.dones == [False]


def test_nonterminal_chunk_bootstraps_current_legal_state_before_update():
    config, scenario = _small_case(2)
    runner = BoundaryAwareEpisodeRunner(
        config=config,
        regime="F",
        scenario=scenario,
        training_seed=41001,
        allow_test_fixture=True,
    )
    agent = runner.architecture.agents["R1"]
    buffer = runner.buffers["R1"]

    for _ in range(256):
        buffer.add(
            observation=np.zeros(4, dtype=np.float32),
            action=np.zeros(1, dtype=np.float32),
            log_prob=0.0,
            reward=0.0,
            value=0.0,
            done=False,
            policy_active=True,
        )

    captured = {}

    def fake_value(observation):
        captured["bootstrap_observation"] = np.asarray(observation).copy()
        return 3.5

    def fake_update(batch):
        captured["batch"] = batch
        return _zero_stats()

    agent.value = fake_value
    agent.updater.update = fake_update
    runner._current_boundary_day = 256

    next_observation = np.asarray([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    runner._before_actor_decision("R1", next_observation, agent)

    assert len(buffer) == 0
    assert len(runner.update_events) == 1
    event = runner.update_events[0]
    assert event.actor == "R1"
    assert event.boundary_day == 256
    assert event.transition_count == 256
    assert event.terminal is False
    assert event.bootstrap_value == pytest.approx(3.5)
    np.testing.assert_allclose(
        captured["bootstrap_observation"],
        next_observation,
    )
    assert float(captured["batch"].returns[-1].cpu()) == pytest.approx(3.5)


def test_terminal_smoke_episode_flushes_with_zero_bootstrap():
    config, scenario = tiny_deterministic_smoke_case()
    runner = BoundaryAwareEpisodeRunner(
        config=config,
        regime="F",
        scenario=scenario,
        training_seed=41001,
        allow_test_fixture=True,
    )
    result = runner.run_episode()

    assert result.rollout_partition == (8,)
    assert len(result.period_df) == 8
    assert len(result.update_events) == 6
    assert {event.actor for event in result.update_events} == set(ACTOR_NAMES)
    assert all(event.terminal for event in result.update_events)
    assert all(event.transition_count == 8 for event in result.update_events)
    assert all(event.bootstrap_value == 0.0 for event in result.update_events)
    assert all(math.isfinite(event.stats.total_loss) for event in result.update_events)


def test_256_chunk_updates_each_actor_before_its_day_256_action():
    horizon = 257
    config = SimulationConfig(
        simulation_horizon_days=horizon,
        warmup_days=0,
        shelf_life_days=7,
        exporter_to_importer_lead_time_days=2,
        importer_to_retailer_lead_time_days=1,
        retailer_mean_demand=(10.0, 10.0, 10.0),
        demand_forecast_smoothing_weight=0.30,
        exporter_availability_probability=(1.0, 1.0),
    )
    demand = np.full((horizon, 3), 10.0, dtype=float)
    availability = np.asarray(
        [[(t % 3) != 0, (t % 4) != 0] for t in range(horizon)],
        dtype=bool,
    )
    scenario = deterministic_scenario(demand, availability, seed=812256)

    runner = BoundaryAwareEpisodeRunner(
        config=config,
        regime="F",
        scenario=scenario,
        training_seed=41001,
        allow_test_fixture=True,
    )
    update_call_count = {actor: 0 for actor in ACTOR_NAMES}
    captured_first_masks = {}

    expected_current_predecessors = {
        "R1": (),
        "R2": ("R1",),
        "R3": ("R1", "R2"),
        "BQ": ("R1", "R2", "R3"),
        "E1": ("R1", "R2", "R3", "BQ"),
        "E2": ("R1", "R2", "R3", "BQ", "E1"),
    }

    for actor in ACTOR_NAMES:
        def make_fake_update(actor_name):
            def fake_update(batch):
                update_call_count[actor_name] += 1
                records = runner.architecture.records_by_actor()

                if update_call_count[actor_name] == 1:
                    captured_first_masks[actor_name] = (
                        batch.policy_mask.detach().cpu().numpy().copy()
                    )
                    assert records[actor_name][-1].day == 255
                    for predecessor in expected_current_predecessors[actor_name]:
                        assert records[predecessor][-1].day == 256

                return _zero_stats()
            return fake_update

        runner.architecture.agents[actor].updater.update = make_fake_update(actor)

    result = runner.run_episode()

    assert result.rollout_partition == (256, 1)
    for actor in ACTOR_NAMES:
        events = [event for event in result.update_events if event.actor == actor]
        assert [event.transition_count for event in events] == [256, 1]
        assert [event.terminal for event in events] == [False, True]
        assert events[0].boundary_day == 256
        assert update_call_count[actor] == 2

    np.testing.assert_array_equal(
        captured_first_masks["E1"],
        availability[:256, 0],
    )
    np.testing.assert_array_equal(
        captured_first_masks["E2"],
        availability[:256, 1],
    )


def test_causal_reward_indexing_preserves_locked_undiscounted_episode_objective():
    config, scenario = _small_case(12)
    frame = SupplyChainModel(config, "F", scenario).run()
    scale = float(sum(config.retailer_mean_demand))

    transition_rewards = physical_team_rewards(
        frame,
        aggregate_mean_demand=scale,
    )
    locked_spec_total = -(
        float(frame["aggregate_lost_sales"].sum())
        + float(frame["total_waste"].sum())
        + float(frame.iloc[-1]["total_on_hand_inventory"])
        + float(frame.iloc[-1]["total_pipeline_inventory"])
    ) / scale

    initial_preaction_constant = (
        float(frame.iloc[0]["aggregate_lost_sales"])
        + float(frame.iloc[0]["transit_waste"])
    ) / scale

    assert float(transition_rewards.sum()) == pytest.approx(
        locked_spec_total + initial_preaction_constant
    )
