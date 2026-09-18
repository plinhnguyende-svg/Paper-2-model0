from __future__ import annotations

import math

import numpy as np
import pytest
import torch

from paper2_model0.ai import (
    ACTOR_NETWORK_SPECS,
    ActorRolloutBuffer,
    GaussianActorCritic,
    PPOHyperparameters,
    PPOTrainingBatch,
    PPOUpdater,
    build_actor_local_ippo_agents,
    compute_gae,
)


def _parameter_snapshot(model):
    return [p.detach().cpu().clone() for p in model.parameters()]


def test_locked_actor_network_specs_match_six_learnable_nodes():
    assert [(x.name, x.observation_dim, x.action_dim) for x in ACTOR_NETWORK_SPECS] == [
        ("R1", 4, 1),
        ("R2", 4, 1),
        ("R3", 4, 1),
        ("BQ", 6, 1),
        ("E1", 7, 1),
        ("E2", 7, 1),
    ]
    assert "allocation" not in {x.name.lower() for x in ACTOR_NETWORK_SPECS}


def test_actor_critic_shapes_and_deterministic_mean_action():
    torch.manual_seed(1)
    model = GaussianActorCritic(observation_dim=4, action_dim=1)
    obs = torch.zeros(3, 4)

    action_1, log_prob_1, value_1 = model.act(obs, deterministic=True)
    action_2, log_prob_2, value_2 = model.act(obs, deterministic=True)

    assert action_1.shape == (3, 1)
    assert log_prob_1.shape == (3,)
    assert value_1.shape == (3,)
    torch.testing.assert_close(action_1, action_2)
    torch.testing.assert_close(log_prob_1, log_prob_2)
    torch.testing.assert_close(value_1, value_2)
    torch.testing.assert_close(action_1, model.actor_mean(obs))


def test_actor_critic_rejects_nonlocal_wrong_dimension():
    model = GaussianActorCritic(observation_dim=4, action_dim=1)
    with pytest.raises(ValueError, match="expected observation dimension 4"):
        model.value(torch.zeros(1, 7))


def test_actor_local_factory_has_no_parameter_or_optimizer_sharing():
    agents = build_actor_local_ippo_agents(training_seed=41001)
    assert set(agents) == {"R1", "R2", "R3", "BQ", "E1", "E2"}

    model_ids = [id(x.network) for x in agents.values()]
    optimizer_ids = [id(x.updater.optimizer) for x in agents.values()]
    parameter_ids = [
        id(p)
        for agent in agents.values()
        for p in agent.network.parameters()
    ]

    assert len(model_ids) == len(set(model_ids)) == 6
    assert len(optimizer_ids) == len(set(optimizer_ids)) == 6
    assert len(parameter_ids) == len(set(parameter_ids))


def test_same_training_seed_reproduces_same_actor_initialization_convention():
    first = build_actor_local_ippo_agents(training_seed=41001)
    second = build_actor_local_ippo_agents(training_seed=41001)

    for name in first:
        first_params = _parameter_snapshot(first[name].network)
        second_params = _parameter_snapshot(second[name].network)
        for a, b in zip(first_params, second_params):
            torch.testing.assert_close(a, b)


def test_distinct_actor_instances_do_not_start_from_shared_parameter_objects():
    agents = build_actor_local_ippo_agents(training_seed=41001)
    r1 = _parameter_snapshot(agents["R1"].network)
    r2 = _parameter_snapshot(agents["R2"].network)

    # Same architecture but actor-specific initialization seed.
    assert any(not torch.equal(a, b) for a, b in zip(r1, r2))


def test_actor_local_agent_checks_its_local_observation_dimension():
    agents = build_actor_local_ippo_agents(training_seed=41001)
    with pytest.raises(ValueError, match="R1 expected observation shape"):
        agents["R1"].act(np.zeros(7, dtype=np.float32), deterministic=True)


def test_ppo_hyperparameters_are_locked_to_merged_specification():
    PPOHyperparameters().validate_locked_v01()
    with pytest.raises(ValueError, match="locked"):
        PPOHyperparameters(clip_range=0.10).validate_locked_v01()


def test_compute_gae_respects_terminal_boundary_with_gamma_one():
    advantages, returns = compute_gae(
        rewards=np.array([1.0, 1.0]),
        values=np.array([0.5, 0.25]),
        dones=np.array([False, True]),
        last_value=10.0,
        gamma=1.0,
        gae_lambda=0.95,
    )

    np.testing.assert_allclose(advantages, [1.4625, 0.75])
    np.testing.assert_allclose(returns, [1.9625, 1.0])


def test_actor_rollout_buffer_stores_only_local_ppo_quantities():
    buffer = ActorRolloutBuffer(observation_dim=4, action_dim=1)
    buffer.add(
        observation=np.array([1.0, 2.0, 3.0, 4.0]),
        action=np.array([0.5]),
        log_prob=-0.2,
        reward=-1.0,
        value=0.3,
        done=False,
    )

    assert set(buffer.__dict__) == {
        "observation_dim",
        "action_dim",
        "observations",
        "actions",
        "log_probs",
        "rewards",
        "values",
        "dones",
        "policy_masks",
    }
    assert not hasattr(buffer, "scenario")
    assert not hasattr(buffer, "regime")
    assert not hasattr(buffer, "global_state")


def test_rollout_buffer_builds_finite_training_batch():
    hp = PPOHyperparameters()
    buffer = ActorRolloutBuffer(observation_dim=4, action_dim=1)
    for i in range(4):
        buffer.add(
            observation=np.full(4, i, dtype=np.float32),
            action=np.array([0.1 * i], dtype=np.float32),
            log_prob=-0.5,
            reward=-float(i),
            value=0.2,
            done=(i == 3),
        )

    batch = buffer.training_batch(
        last_value=0.0,
        hyperparameters=hp,
    )
    assert batch.observations.shape == (4, 4)
    assert batch.actions.shape == (4, 1)
    assert torch.isfinite(batch.returns).all()
    assert torch.isfinite(batch.advantages).all()


def test_ppo_update_is_finite_and_changes_only_local_model_parameters():
    torch.manual_seed(123)
    model = GaussianActorCritic(observation_dim=4, action_dim=1)
    updater = PPOUpdater(model, shuffle_seed=999)
    hp = PPOHyperparameters()

    rng = np.random.default_rng(123)
    observations = torch.tensor(
        rng.normal(size=(64, 4)),
        dtype=torch.float32,
    )

    with torch.no_grad():
        actions, old_log_probs, old_values = model.act(
            observations,
            deterministic=False,
        )

    advantages = torch.tensor(
        rng.normal(size=64),
        dtype=torch.float32,
    )
    returns = old_values.detach() + advantages

    batch = PPOTrainingBatch(
        observations=observations,
        actions=actions.detach(),
        old_log_probs=old_log_probs.detach(),
        returns=returns.detach(),
        advantages=advantages,
    )

    before = _parameter_snapshot(model)
    stats = updater.update(batch)
    after = _parameter_snapshot(model)

    assert stats.minibatch_updates == hp.update_epochs
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
    assert 0.0 <= stats.clip_fraction <= 1.0
    assert any(not torch.equal(a, b) for a, b in zip(before, after))


def test_ppo_update_rejects_nonfinite_training_data():
    model = GaussianActorCritic(observation_dim=4, action_dim=1)
    updater = PPOUpdater(model, shuffle_seed=1)
    batch = PPOTrainingBatch(
        observations=torch.zeros(2, 4),
        actions=torch.zeros(2, 1),
        old_log_probs=torch.tensor([0.0, float("nan")]),
        returns=torch.zeros(2),
        advantages=torch.ones(2),
    )
    with pytest.raises(ValueError, match="non-finite"):
        updater.update(batch)


def test_fully_masked_policy_batch_updates_critic_but_not_actor():
    torch.manual_seed(321)
    model = GaussianActorCritic(observation_dim=7, action_dim=1)
    updater = PPOUpdater(model, shuffle_seed=1234)

    observations = torch.randn(8, 7)
    with torch.no_grad():
        actions, old_log_probs, values = model.act(
            observations,
            deterministic=True,
        )

    batch = PPOTrainingBatch(
        observations=observations,
        actions=actions.detach(),
        old_log_probs=old_log_probs.detach(),
        returns=(values.detach() + 1.0),
        advantages=torch.ones(8),
        policy_mask=torch.zeros(8, dtype=torch.bool),
    )

    actor_before = [
        p.detach().clone()
        for p in model.actor_mean.parameters()
    ]
    log_std_before = model.log_std.detach().clone()
    critic_before = [
        p.detach().clone()
        for p in model.critic.parameters()
    ]

    stats = updater.update(batch)

    actor_after = list(model.actor_mean.parameters())
    critic_after = list(model.critic.parameters())

    assert all(
        torch.equal(before, after.detach())
        for before, after in zip(actor_before, actor_after)
    )
    assert torch.equal(log_std_before, model.log_std.detach())
    assert any(
        not torch.equal(before, after.detach())
        for before, after in zip(critic_before, critic_after)
    )
    assert stats.policy_loss == pytest.approx(0.0)
    assert stats.entropy == pytest.approx(0.0)
    assert stats.approximate_kl == pytest.approx(0.0)
    assert stats.clip_fraction == pytest.approx(0.0)
