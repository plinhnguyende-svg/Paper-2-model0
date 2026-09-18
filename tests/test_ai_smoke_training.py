from __future__ import annotations

import math

import numpy as np
import pandas as pd
import torch

from paper2_model0.ai import (
    ActorLocalAIDecisionArchitecture,
    build_actor_local_ippo_agents,
    physical_team_rewards,
    run_tiny_smoke_training,
    tiny_deterministic_smoke_case,
)
from paper2_model0.engine.model import SupplyChainModel


def _all_finite_stats(result):
    for stats in result.update_stats.values():
        for value in (
            stats.policy_loss,
            stats.value_loss,
            stats.entropy,
            stats.total_loss,
            stats.approximate_kl,
            stats.clip_fraction,
            stats.gradient_norm,
        ):
            assert math.isfinite(value)


def test_actor_local_stochastic_action_stream_is_reproducible_and_global_rng_safe():
    obs = np.array([1.0, 0.5, 0.2, 1.1], dtype=np.float32)

    first = build_actor_local_ippo_agents(training_seed=41001)["R1"]
    torch.manual_seed(999999)
    action_1a, logp_1a, value_1a = first.act(obs, deterministic=False)
    torch.manual_seed(123)
    action_1b, logp_1b, value_1b = first.act(obs, deterministic=False)

    second = build_actor_local_ippo_agents(training_seed=41001)["R1"]
    torch.manual_seed(7)
    action_2a, logp_2a, value_2a = second.act(obs, deterministic=False)
    torch.manual_seed(8)
    action_2b, logp_2b, value_2b = second.act(obs, deterministic=False)

    np.testing.assert_allclose(action_1a, action_2a)
    np.testing.assert_allclose(action_1b, action_2b)
    assert logp_1a == logp_2a
    assert logp_1b == logp_2b
    assert value_1a == value_2a
    assert value_1b == value_2b


def test_physical_team_reward_uses_period_loss_waste_and_terminal_leftover():
    frame = pd.DataFrame(
        {
            "aggregate_lost_sales": [3.0, 6.0],
            "on_hand_waste": [1.0, 3.0],
            "transit_waste": [7.0, 2.0],
            "total_on_hand_inventory": [100.0, 30.0],
            "total_pipeline_inventory": [20.0, 15.0],
        }
    )
    reward = physical_team_rewards(
        frame,
        aggregate_mean_demand=30.0,
    )
    np.testing.assert_allclose(
        reward,
        [
            -(1.0 + 6.0 + 2.0) / 30.0,
            -(3.0) / 30.0 - (30.0 + 15.0) / 30.0,
        ],
    )


def test_ai_decision_architecture_runs_through_all_three_information_regimes():
    config, scenario = tiny_deterministic_smoke_case()

    for regime in ("N", "S", "F"):
        architecture = ActorLocalAIDecisionArchitecture(
            config,
            training_seed=41001,
            deterministic=True,
        )
        frame = SupplyChainModel(
            config,
            regime,
            scenario,
            decision_architecture=architecture,
        ).run()

        assert len(frame) == config.simulation_horizon_days
        assert architecture.records_by_actor().keys() == {
            "R1", "R2", "R3", "BQ", "E1", "E2"
        }
        assert all(
            len(records) == config.simulation_horizon_days
            for records in architecture.records_by_actor().values()
        )

        # Importer allocation remains the frozen institutional mechanism.
        if regime == "N":
            np.testing.assert_allclose(
                frame["allocation_1"].to_numpy(),
                0.5 * frame["procurement_requirement"].to_numpy(),
            )
            np.testing.assert_allclose(
                frame["allocation_2"].to_numpy(),
                0.5 * frame["procurement_requirement"].to_numpy(),
            )
        else:
            for row in frame.itertuples():
                active = row.availability_1 + row.availability_2
                if active == 0:
                    assert row.allocation_1 == 0.0
                    assert row.allocation_2 == 0.0
                else:
                    assert row.allocation_1 == (
                        row.procurement_requirement * row.availability_1 / active
                    )
                    assert row.allocation_2 == (
                        row.procurement_requirement * row.availability_2 / active
                    )


def test_tiny_smoke_training_is_end_to_end_for_N_S_F():
    config, scenario = tiny_deterministic_smoke_case()

    results = [
        run_tiny_smoke_training(
            regime=regime,
            config=config,
            scenario=scenario,
            training_seed=41001,
        )
        for regime in ("N", "S", "F")
    ]

    assert {result.regime for result in results} == {"N", "S", "F"}
    assert {result.scenario_id for result in results} == {scenario.scenario_id}

    for result in results:
        assert result.horizon_days == 8
        assert math.isfinite(result.total_team_reward)
        assert result.actor_buffer_lengths == {
            "R1": 8,
            "R2": 8,
            "R3": 8,
            "BQ": 8,
            "E1": 8,
            "E2": 8,
        }
        assert all(result.parameter_changed.values())
        _all_finite_stats(result)


def test_tiny_smoke_training_is_reproducible_for_fixed_seed_and_scenario():
    config, scenario = tiny_deterministic_smoke_case()

    first = run_tiny_smoke_training(
        regime="F",
        config=config,
        scenario=scenario,
        training_seed=41001,
    )
    second = run_tiny_smoke_training(
        regime="F",
        config=config,
        scenario=scenario,
        training_seed=41001,
    )

    assert first.scenario_id == second.scenario_id
    assert first.total_team_reward == second.total_team_reward
    assert first.actor_buffer_lengths == second.actor_buffer_lengths
    assert first.parameter_changed == second.parameter_changed

    for actor in first.update_stats:
        a = first.update_stats[actor]
        b = second.update_stats[actor]
        assert a == b


def test_unavailable_exporter_keeps_critic_timeline_but_masks_policy_gradient():
    config, scenario = tiny_deterministic_smoke_case()
    architecture = ActorLocalAIDecisionArchitecture(
        config,
        training_seed=41001,
        deterministic=False,
    )
    frame = SupplyChainModel(
        config,
        "F",
        scenario,
        decision_architecture=architecture,
    ).run()

    from paper2_model0.ai import build_episode_rollout_buffers

    buffers, _ = build_episode_rollout_buffers(
        architecture=architecture,
        period_df=frame,
    )

    for actor, availability_col in (
        ("E1", "availability_1"),
        ("E2", "availability_2"),
    ):
        mask = np.asarray(buffers[actor].policy_masks, dtype=bool)
        availability = frame[availability_col].to_numpy(dtype=bool)
        np.testing.assert_array_equal(mask, availability)
        assert len(mask) == config.simulation_horizon_days
        assert np.any(~mask)
        assert np.any(mask)


def test_day_zero_lost_sales_is_not_attributed_to_same_day_action():
    frame = pd.DataFrame(
        {
            "aggregate_lost_sales": [30.0, 0.0],
            "on_hand_waste": [0.0, 0.0],
            "transit_waste": [0.0, 0.0],
            "total_on_hand_inventory": [0.0, 0.0],
            "total_pipeline_inventory": [0.0, 0.0],
        }
    )
    reward = physical_team_rewards(
        frame,
        aggregate_mean_demand=30.0,
    )
    np.testing.assert_allclose(reward, [0.0, 0.0])


def test_day_zero_transit_waste_is_not_attributed_to_same_day_action():
    frame = pd.DataFrame(
        {
            "aggregate_lost_sales": [0.0, 0.0],
            "on_hand_waste": [0.0, 0.0],
            "transit_waste": [30.0, 0.0],
            "total_on_hand_inventory": [0.0, 0.0],
            "total_pipeline_inventory": [0.0, 0.0],
        }
    )
    reward = physical_team_rewards(
        frame,
        aggregate_mean_demand=30.0,
    )
    np.testing.assert_allclose(reward, [0.0, 0.0])
