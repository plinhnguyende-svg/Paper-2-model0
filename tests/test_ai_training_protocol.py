from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas.testing as pdt
import pytest
import torch

from paper2_model0.ai import (
    ACTOR_NAMES,
    ActorLocalAIDecisionArchitecture,
    BoundaryAwareEpisodeRunner,
    CHECKPOINT_VERSION,
    EVALUATION_MASTER_SEED,
    INFORMATION_REGIMES,
    PPOHyperparameters,
    SCENARIO_SEED_PROTOCOL_VERSION,
    TRAINING_EPISODES,
    TRAINING_SEEDS,
    build_run_manifest,
    checkpoint_payload,
    episode_manifest_record,
    episode_scenario_seed,
    episode_seed_schedule,
    load_training_checkpoint,
    run_manifest_hash,
    save_training_checkpoint,
    tiny_deterministic_smoke_case,
    training_run_keys,
    validate_run_manifest,
    validate_scientific_training_contract,
)
from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import deterministic_scenario, generate_scenario


SOURCE_COMMIT_SHA = "e0b09d602518b546d05696bee853855aae608ee6"


def _second_smoke_scenario(config: SimulationConfig):
    horizon = config.simulation_horizon_days
    demand = np.asarray(
        [
            [9 + (t % 4), 11 - (t % 3), 10 + (t % 2)]
            for t in range(horizon)
        ],
        dtype=float,
    )
    availability = np.asarray(
        [
            [(t % 3) != 1, (t % 4) != 2]
            for t in range(horizon)
        ],
        dtype=bool,
    )
    return deterministic_scenario(demand, availability, seed=909002)


def _assert_nested_equal(left, right):
    if isinstance(left, torch.Tensor):
        assert isinstance(right, torch.Tensor)
        torch.testing.assert_close(left, right, rtol=0.0, atol=0.0)
        return
    if isinstance(left, dict):
        assert set(left) == set(right)
        for key in left:
            _assert_nested_equal(left[key], right[key])
        return
    if isinstance(left, (list, tuple)):
        assert type(left) is type(right)
        assert len(left) == len(right)
        for a, b in zip(left, right):
            _assert_nested_equal(a, b)
        return
    assert left == right


def _assert_actor_states_equal(left, right):
    for actor in ACTOR_NAMES:
        a = left.agents[actor]
        b = right.agents[actor]
        for key, value in a.network.state_dict().items():
            torch.testing.assert_close(
                value,
                b.network.state_dict()[key],
                rtol=0.0,
                atol=0.0,
            )
        assert torch.equal(
            a.action_generator.get_state(),
            b.action_generator.get_state(),
        )
        assert torch.equal(
            a.updater._shuffle_generator.get_state(),
            b.updater._shuffle_generator.get_state(),
        )
        _assert_nested_equal(
            a.updater.optimizer.state_dict(),
            b.updater.optimizer.state_dict(),
        )


def test_training_scenario_schedule_is_regime_independent_and_eval_seed_reserved():
    config = SimulationConfig(
        simulation_horizon_days=8,
        warmup_days=0,
    )
    sampled_indices = (0, 1, 17, 999)

    for training_seed in TRAINING_SEEDS:
        for episode_index in sampled_indices:
            seed = episode_scenario_seed(training_seed, episode_index)
            assert seed != EVALUATION_MASTER_SEED

            ids = []
            for _regime in INFORMATION_REGIMES:
                scenario = generate_scenario(config, seed)
                ids.append(scenario.scenario_id)
                assert scenario.replication_seed == seed
            assert len(set(ids)) == 1

    schedule = episode_seed_schedule(41001, episode_count=20)
    assert len(schedule) == 20
    assert schedule == episode_seed_schedule(41001, episode_count=20)
    assert EVALUATION_MASTER_SEED not in schedule

    full_locked_domain = [
        episode_scenario_seed(training_seed, episode_index)
        for training_seed in TRAINING_SEEDS
        for episode_index in range(TRAINING_EPISODES)
    ]
    assert len(full_locked_domain) == 5000
    assert len(set(full_locked_domain)) == 5000
    assert EVALUATION_MASTER_SEED not in full_locked_domain


def test_seed_schedule_rejects_unregistered_seed_and_budget_extension():
    with pytest.raises(ValueError, match="pre-registered"):
        episode_scenario_seed(52001, 0)
    with pytest.raises(ValueError, match="episode_count"):
        episode_seed_schedule(41001, episode_count=TRAINING_EPISODES + 1)


def test_manifest_is_complete_hash_bound_and_schedule_checked():
    config = SimulationConfig()
    seed = episode_scenario_seed(41001, 0)
    scenario = generate_scenario(config, seed)
    record = episode_manifest_record(
        training_seed=41001,
        episode_index=0,
        scenario=scenario,
    )
    manifest = build_run_manifest(
        regime="S",
        training_seed=41001,
        config=config,
        source_commit_sha=SOURCE_COMMIT_SHA,
        episode_records=[record],
    )

    assert manifest["checkpoint_version"] == CHECKPOINT_VERSION
    assert (
        manifest["scenario_seed_protocol_version"]
        == SCENARIO_SEED_PROTOCOL_VERSION
    )
    assert manifest["completed_episode_count"] == 1
    assert manifest["episodes"] == [record]
    assert manifest["episode_budget"] == 1000
    assert manifest["episode_horizon_days"] == 1000
    assert manifest["rollout_length_days"] == 256
    assert len(manifest["simulation_config_sha256"]) == 64
    validate_run_manifest(manifest)

    tampered = deepcopy(manifest)
    tampered["episodes"][0]["episode_seed"] += 1
    with pytest.raises(ValueError, match="locked schedule"):
        validate_run_manifest(tampered)


def test_scientific_manifest_rejects_horizon_drift():
    config = SimulationConfig(
        simulation_horizon_days=999,
        warmup_days=200,
    )
    with pytest.raises(ValueError, match="1000 Model-0 days"):
        build_run_manifest(
            regime="N",
            training_seed=41001,
            config=config,
            source_commit_sha=SOURCE_COMMIT_SHA,
        )


def test_checkpoint_contains_all_six_network_optimizer_and_rng_states():
    config, _ = tiny_deterministic_smoke_case()
    architecture = ActorLocalAIDecisionArchitecture(
        config,
        training_seed=41001,
        deterministic=False,
    )
    payload = checkpoint_payload(
        architecture=architecture,
        regime="F",
        completed_episode_count=0,
        config=config,
    )

    assert set(payload["actors"]) == set(ACTOR_NAMES)
    for actor_state in payload["actors"].values():
        assert set(actor_state) == {
            "network",
            "updater",
            "action_generator_state",
        }
        assert set(actor_state["updater"]) == {
            "optimizer",
            "shuffle_generator_state",
        }
        assert isinstance(actor_state["action_generator_state"], torch.Tensor)
        assert isinstance(
            actor_state["updater"]["shuffle_generator_state"],
            torch.Tensor,
        )


def test_uninterrupted_and_save_resume_match_next_actions_and_subsequent_updates(
    tmp_path,
):
    config, first_scenario = tiny_deterministic_smoke_case()
    second_scenario = _second_smoke_scenario(config)

    uninterrupted_architecture = ActorLocalAIDecisionArchitecture(
        config,
        training_seed=41001,
        deterministic=False,
    )
    first_runner = BoundaryAwareEpisodeRunner(
        config=config,
        regime="F",
        scenario=first_scenario,
        training_seed=41001,
        architecture=uninterrupted_architecture,        allow_test_fixture=True,
    )
    first_runner.run_episode()

    checkpoint_path = tmp_path / "recovery.pt"
    save_training_checkpoint(
        checkpoint_path,
        architecture=uninterrupted_architecture,
        regime="F",
        completed_episode_count=1,
        config=config,
    )

    uninterrupted_second = BoundaryAwareEpisodeRunner(
        config=config,
        regime="F",
        scenario=second_scenario,
        training_seed=41001,
        architecture=uninterrupted_architecture,        allow_test_fixture=True,
    ).run_episode()

    resumed_architecture, metadata = load_training_checkpoint(
        checkpoint_path,
        config=config,
        expected_regime="F",
        expected_training_seed=41001,
    )
    assert metadata["completed_episode_count"] == 1

    resumed_second = BoundaryAwareEpisodeRunner(
        config=config,
        regime="F",
        scenario=second_scenario,
        training_seed=41001,
        architecture=resumed_architecture,        allow_test_fixture=True,
    ).run_episode()

    pdt.assert_frame_equal(
        uninterrupted_second.period_df,
        resumed_second.period_df,
        check_exact=True,
    )
    assert uninterrupted_second.update_events == resumed_second.update_events

    for actor in ACTOR_NAMES:
        uninterrupted_records = uninterrupted_architecture.records_by_actor()[actor]
        resumed_records = resumed_architecture.records_by_actor()[actor]
        assert len(uninterrupted_records) == len(resumed_records) == 8
        for left, right in zip(uninterrupted_records, resumed_records):
            np.testing.assert_array_equal(
                left.latent_action,
                right.latent_action,
            )
            np.testing.assert_array_equal(
                left.observation,
                right.observation,
            )
            assert left.log_prob == right.log_prob
            assert left.value == right.value
            assert left.policy_active == right.policy_active

    _assert_actor_states_equal(
        uninterrupted_architecture,
        resumed_architecture,
    )


def test_checkpoint_resume_rejects_regime_seed_and_config_drift(tmp_path):
    config, _ = tiny_deterministic_smoke_case()
    architecture = ActorLocalAIDecisionArchitecture(
        config,
        training_seed=41001,
        deterministic=False,
    )
    path = save_training_checkpoint(
        tmp_path / "state.pt",
        architecture=architecture,
        regime="S",
        completed_episode_count=4,
        config=config,
    )

    with pytest.raises(ValueError, match="regime"):
        load_training_checkpoint(
            path,
            config=config,
            expected_regime="F",
            expected_training_seed=41001,
        )
    with pytest.raises(ValueError, match="training seed"):
        load_training_checkpoint(
            path,
            config=config,
            expected_regime="S",
            expected_training_seed=41002,
        )

    drifted = SimulationConfig(
        simulation_horizon_days=8,
        warmup_days=0,
        shelf_life_days=4,
    )
    with pytest.raises(ValueError, match="config"):
        load_training_checkpoint(
            path,
            config=drifted,
            expected_regime="S",
            expected_training_seed=41001,
        )


def test_non_finite_actor_state_fails_before_checkpoint_and_action(tmp_path):
    config, _ = tiny_deterministic_smoke_case()
    architecture = ActorLocalAIDecisionArchitecture(
        config,
        training_seed=41001,
        deterministic=False,
    )
    agent = architecture.agents["R1"]
    with torch.no_grad():
        next(agent.network.parameters()).fill_(float("nan"))

    observation = np.zeros(
        agent.network.observation_dim,
        dtype=np.float32,
    )
    with pytest.raises(FloatingPointError, match="non-finite"):
        agent.act(observation, deterministic=False)

    with pytest.raises(FloatingPointError, match="non-finite"):
        save_training_checkpoint(
            tmp_path / "bad.pt",
            architecture=architecture,
            regime="N",
            completed_episode_count=0,
            config=config,
        )


def test_episode_boundary_resets_only_diagnostic_traces_not_learning_state():
    config, first_scenario = tiny_deterministic_smoke_case()
    second_scenario = _second_smoke_scenario(config)

    architecture = ActorLocalAIDecisionArchitecture(
        config,
        training_seed=41001,
        deterministic=False,
    )
    BoundaryAwareEpisodeRunner(
        config=config,
        regime="N",
        scenario=first_scenario,
        training_seed=41001,
        architecture=architecture,        allow_test_fixture=True,
    ).run_episode()

    first_network_state = {
        actor: {
            key: value.detach().clone()
            for key, value in architecture.agents[actor].network.state_dict().items()
        }
        for actor in ACTOR_NAMES
    }
    first_action_rng = {
        actor: architecture.agents[actor].action_generator.get_state().clone()
        for actor in ACTOR_NAMES
    }
    assert all(
        len(records) == config.simulation_horizon_days
        for records in architecture.records_by_actor().values()
    )

    second_runner = BoundaryAwareEpisodeRunner(
        config=config,
        regime="N",
        scenario=second_scenario,
        training_seed=41001,
        architecture=architecture,        allow_test_fixture=True,
    )

    assert all(
        len(records) == 0
        for records in architecture.records_by_actor().values()
    )
    for actor in ACTOR_NAMES:
        # Constructing the next episode must not reinitialize the learned state.
        for key, value in architecture.agents[actor].network.state_dict().items():
            torch.testing.assert_close(
                value,
                first_network_state[actor][key],
                rtol=0.0,
                atol=0.0,
            )
        assert torch.equal(
            architecture.agents[actor].action_generator.get_state(),
            first_action_rng[actor],
        )

    second_runner.run_episode()
    assert all(
        len(records) == config.simulation_horizon_days
        for records in architecture.records_by_actor().values()
    )


def test_scientific_contract_exposes_exactly_15_locked_run_keys():
    assert training_run_keys() == tuple(
        (regime, seed)
        for regime in ("N", "S", "F")
        for seed in (41001, 41002, 41003, 41004, 41005)
    )
    assert len(training_run_keys()) == 15

    validate_scientific_training_contract(
        regime="F",
        training_seed=41005,
        config=SimulationConfig(),
        hyperparameters=PPOHyperparameters(),
    )

    with pytest.raises(ValueError, match="pre-registered"):
        validate_scientific_training_contract(
            regime="F",
            training_seed=99999,
            config=SimulationConfig(),
        )
    with pytest.raises(ValueError, match="1000 Model-0 days"):
        validate_scientific_training_contract(
            regime="F",
            training_seed=41001,
            config=SimulationConfig(simulation_horizon_days=999),
        )
    with pytest.raises(ValueError, match="locked"):
        validate_scientific_training_contract(
            regime="F",
            training_seed=41001,
            config=SimulationConfig(),
            hyperparameters=PPOHyperparameters(clip_range=0.10),
        )


def test_scientific_checkpoint_is_cryptographically_bound_to_manifest(tmp_path):
    config = SimulationConfig()
    architecture = ActorLocalAIDecisionArchitecture(
        config,
        training_seed=41001,
        deterministic=False,
    )
    manifest = build_run_manifest(
        regime="N",
        training_seed=41001,
        config=config,
        source_commit_sha=SOURCE_COMMIT_SHA,
    )
    path = save_training_checkpoint(
        tmp_path / "scientific.pt",
        architecture=architecture,
        regime="N",
        completed_episode_count=0,
        config=config,
        manifest=manifest,
    )

    resumed, metadata = load_training_checkpoint(
        path,
        config=config,
        expected_regime="N",
        expected_training_seed=41001,
        expected_manifest=manifest,
    )
    assert metadata["run_manifest_sha256"] == run_manifest_hash(manifest)
    _assert_actor_states_equal(architecture, resumed)

    tampered = deepcopy(manifest)
    tampered["source_commit_sha"] = "1" * 40
    with pytest.raises(ValueError, match="run-manifest hash"):
        load_training_checkpoint(
            path,
            config=config,
            expected_regime="N",
            expected_training_seed=41001,
            expected_manifest=tampered,
        )


def test_scientific_checkpoint_cannot_omit_manifest(tmp_path):
    config = SimulationConfig()
    architecture = ActorLocalAIDecisionArchitecture(
        config,
        training_seed=41001,
        deterministic=False,
    )
    with pytest.raises(ValueError, match="requires its run manifest"):
        save_training_checkpoint(
            tmp_path / "unbound.pt",
            architecture=architecture,
            regime="N",
            completed_episode_count=0,
            config=config,
        )
