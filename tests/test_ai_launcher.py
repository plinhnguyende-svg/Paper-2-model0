from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from paper2_model0.ai.environment import ActorLocalAIDecisionArchitecture
from paper2_model0.ai.launcher import (
    FROZEN_LAUNCHER_SHA_ENV,
    FULL_TRAINING_AUTH_ENV,
    FROZEN_RUNNER_BASE,
    LAUNCHER_PROTOCOL_VERSION,
    LOCKED_TRAINING_DEVICE,
    LauncherRunStore,
    build_dry_run_contract,
    build_launcher_manifest,
    compute_training_stability,
    episode_diagnostics,
    load_or_initialize_locked_job,
    locked_job,
    locked_job_registry,
    locked_simulation_config,
    require_full_training_authorization,
    validate_launcher_device,
    validate_launcher_manifest,
)
from paper2_model0.ai.training_protocol import (
    TRAINING_EPISODES,
    episode_manifest_record,
    episode_scenario_seed,
)
from paper2_model0.ai.training_runner import BoundaryAwareEpisodeRunner
from paper2_model0.ai.environment import tiny_deterministic_smoke_case
from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import generate_scenario


SOURCE_SHA = "1" * 40


def test_dry_run_registry_is_exactly_15_unique_locked_jobs():
    jobs = locked_job_registry()
    assert [(job.regime, job.training_seed) for job in jobs] == [
        (regime, seed)
        for regime in ("N", "S", "F")
        for seed in (41001, 41002, 41003, 41004, 41005)
    ]
    assert len({job.job_id for job in jobs}) == 15
    assert len({job.relative_directory.as_posix() for job in jobs}) == 15

    plan = build_dry_run_contract()
    assert plan["job_count"] == 15
    assert plan["episode_count_per_job"] == 1000
    assert plan["episode_horizon_days"] == 1000
    assert plan["full_training_authorized"] is False
    assert plan["frozen_runner_base"] == FROZEN_RUNNER_BASE
    assert plan["locked_training_device"] == LOCKED_TRAINING_DEVICE

    for row in plan["jobs"]:
        seed = row["training_seed"]
        assert row["first_episode_seed"] == episode_scenario_seed(seed, 0)
        assert row["last_episode_seed"] == episode_scenario_seed(seed, 999)


def test_launcher_rejects_arbitrary_job_and_config_drift():
    with pytest.raises(ValueError, match="pre-registered"):
        locked_job("F", 99999)

    drifted = SimulationConfig(shelf_life_days=8)
    with pytest.raises(ValueError, match="exact locked"):
        build_launcher_manifest(
            job=locked_job("N", 41001),
            config=drifted,
            source_commit_sha=SOURCE_SHA,
        )


def test_launcher_device_is_locked_to_cpu():
    validate_launcher_device("cpu")
    with pytest.raises(ValueError, match="CPU"):
        validate_launcher_device("cuda")


def test_manifest_rejects_noncanonical_scenario_id():
    job = locked_job("S", 41001)
    config = locked_simulation_config()
    seed = episode_scenario_seed(job.training_seed, 0)
    scenario = generate_scenario(config, seed)
    record = episode_manifest_record(
        training_seed=job.training_seed,
        episode_index=0,
        scenario=scenario,
    )
    manifest = build_launcher_manifest(
        job=job,
        config=config,
        source_commit_sha=SOURCE_SHA,
        episode_records=[record],
    )
    manifest["episodes"][0]["scenario_id"] = "tampered-scenario"

    with pytest.raises(ValueError, match="scenario_id"):
        validate_launcher_manifest(manifest)


def test_manifest_exists_before_episode_zero_and_resume_is_exact_next(tmp_path):
    job = locked_job("N", 41001)
    config = locked_simulation_config()

    state0 = load_or_initialize_locked_job(
        output_root=tmp_path,
        job=job,
        source_commit_sha=SOURCE_SHA,
        config=config,
    )
    assert state0.next_episode_index == 0
    assert state0.manifest["completed_episode_count"] == 0
    assert state0.manifest["launcher_protocol_version"] == LAUNCHER_PROTOCOL_VERSION

    store = LauncherRunStore(tmp_path, job)
    records = []
    diagnostics = []
    architecture = state0.architecture

    for episode_index in range(2):
        episode_seed = episode_scenario_seed(job.training_seed, episode_index)
        scenario = generate_scenario(config, episode_seed)
        records.append(
            episode_manifest_record(
                training_seed=job.training_seed,
                episode_index=episode_index,
                scenario=scenario,
            )
        )
        diagnostics.append(
            {
                "episode_index": episode_index,
                "episode_seed": episode_seed,
                "scenario_id": scenario.scenario_id,
                "total_team_reward": -1.0,
                "non_finite_event_count": 0,
            }
        )
        manifest = build_launcher_manifest(
            job=job,
            config=config,
            source_commit_sha=SOURCE_SHA,
            episode_records=records,
        )
        store.commit_episode_boundary(
            config=config,
            architecture=architecture,
            manifest=manifest,
            diagnostics=diagnostics,
        )

    resumed = load_or_initialize_locked_job(
        output_root=tmp_path,
        job=job,
        source_commit_sha=SOURCE_SHA,
        config=config,
    )
    assert resumed.next_episode_index == 2
    assert resumed.manifest["completed_episode_count"] == 2
    assert len(resumed.diagnostics) == 2
    assert episode_scenario_seed(job.training_seed, resumed.next_episode_index) == (
        job.training_seed * 1000 + 2
    )

    # Replay or skipping is forbidden by the pointer semantics.
    with pytest.raises(ValueError, match="exact next episode"):
        store.commit_episode_boundary(
            config=config,
            architecture=resumed.architecture,
            manifest=resumed.manifest,
            diagnostics=list(resumed.diagnostics),
        )


def test_resume_removes_uncommitted_higher_episode_orphans(tmp_path):
    job = locked_job("S", 41001)
    config = locked_simulation_config()
    load_or_initialize_locked_job(
        output_root=tmp_path,
        job=job,
        source_commit_sha=SOURCE_SHA,
        config=config,
    )
    store = LauncherRunStore(tmp_path, job)

    orphan_manifest = store.manifest_path(1)
    orphan_checkpoint = store.checkpoint_path(1)
    orphan_manifest_temp = Path(str(orphan_manifest) + ".tmp")
    orphan_checkpoint_temp = Path(str(orphan_checkpoint) + ".tmp")
    diagnostics_temp = Path(str(store.diagnostics_path) + ".tmp")
    orphan_manifest.parent.mkdir(parents=True, exist_ok=True)
    store.diagnostics_path.parent.mkdir(parents=True, exist_ok=True)

    orphan_manifest.write_text("{}\n", encoding="utf-8")
    orphan_checkpoint.write_bytes(b"orphan")
    orphan_manifest_temp.write_text("partial", encoding="utf-8")
    orphan_checkpoint_temp.write_bytes(b"partial")
    diagnostics_temp.write_text("partial", encoding="utf-8")

    resumed = store.load_committed_state(
        config=config,
        source_commit_sha=SOURCE_SHA,
    )
    assert resumed.next_episode_index == 0
    for path in (
        orphan_manifest,
        orphan_checkpoint,
        orphan_manifest_temp,
        orphan_checkpoint_temp,
        diagnostics_temp,
    ):
        assert not path.exists()


def test_resume_truncates_diagnostics_written_ahead_of_latest_pointer(tmp_path):
    job = locked_job("F", 41001)
    config = locked_simulation_config()
    load_or_initialize_locked_job(
        output_root=tmp_path,
        job=job,
        source_commit_sha=SOURCE_SHA,
        config=config,
    )
    store = LauncherRunStore(tmp_path, job)
    store.diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "episode_index": 0,
                "episode_seed": episode_scenario_seed(41001, 0),
                "scenario_id": "orphan",
                "total_team_reward": -1.0,
                "non_finite_event_count": 0,
            }
        ]
    ).to_csv(store.diagnostics_path, index=False)

    resumed = store.load_committed_state(
        config=config,
        source_commit_sha=SOURCE_SHA,
    )
    assert resumed.next_episode_index == 0
    assert not store.diagnostics_path.exists()


def test_commit_rejects_diagnostic_manifest_mismatch_and_source_rewrite(tmp_path):
    job = locked_job("N", 41001)
    config = locked_simulation_config()
    state = load_or_initialize_locked_job(
        output_root=tmp_path,
        job=job,
        source_commit_sha=SOURCE_SHA,
        config=config,
    )
    store = LauncherRunStore(tmp_path, job)
    seed0 = episode_scenario_seed(job.training_seed, 0)
    scenario0 = generate_scenario(config, seed0)
    record0 = episode_manifest_record(
        training_seed=job.training_seed,
        episode_index=0,
        scenario=scenario0,
    )
    manifest0 = build_launcher_manifest(
        job=job,
        config=config,
        source_commit_sha=SOURCE_SHA,
        episode_records=[record0],
    )
    bad_diagnostics = [
        {
            "episode_index": 0,
            "episode_seed": seed0,
            "scenario_id": "wrong",
            "total_team_reward": -1.0,
            "non_finite_event_count": 0,
        }
    ]
    with pytest.raises(ValueError, match="scenario_id"):
        store.commit_episode_boundary(
            config=config,
            architecture=state.architecture,
            manifest=manifest0,
            diagnostics=bad_diagnostics,
        )

    good_diagnostics = [
        {
            "episode_index": 0,
            "episode_seed": seed0,
            "scenario_id": scenario0.scenario_id,
            "total_team_reward": -1.0,
            "non_finite_event_count": 0,
        }
    ]
    store.commit_episode_boundary(
        config=config,
        architecture=state.architecture,
        manifest=manifest0,
        diagnostics=good_diagnostics,
    )

    seed1 = episode_scenario_seed(job.training_seed, 1)
    scenario1 = generate_scenario(config, seed1)
    record1 = episode_manifest_record(
        training_seed=job.training_seed,
        episode_index=1,
        scenario=scenario1,
    )
    rewritten = build_launcher_manifest(
        job=job,
        config=config,
        source_commit_sha="2" * 40,
        episode_records=[record0, record1],
    )
    next_diagnostics = [
        *good_diagnostics,
        {
            "episode_index": 1,
            "episode_seed": seed1,
            "scenario_id": scenario1.scenario_id,
            "total_team_reward": -1.0,
            "non_finite_event_count": 0,
        },
    ]
    with pytest.raises(ValueError, match="source commit"):
        store.commit_episode_boundary(
            config=config,
            architecture=state.architecture,
            manifest=rewritten,
            diagnostics=next_diagnostics,
        )


def test_episode_diagnostics_writer_captures_losses_actions_and_active_fractions():
    config, scenario = tiny_deterministic_smoke_case()
    architecture = ActorLocalAIDecisionArchitecture(
        config,
        training_seed=41001,
        deterministic=False,
    )
    result = BoundaryAwareEpisodeRunner(
        config=config,
        regime="F",
        scenario=scenario,
        training_seed=41001,
        architecture=architecture,
        allow_test_fixture=True,
    ).run_episode()

    row = episode_diagnostics(
        result=result,
        architecture=architecture,
        episode_index=0,
        episode_seed=episode_scenario_seed(41001, 0),
    )

    assert np.isfinite(row["total_team_reward"])
    assert row["non_finite_event_count"] == 0
    for actor in ("R1", "R2", "R3", "BQ", "E1", "E2"):
        for metric in (
            "policy_loss",
            "value_loss",
            "entropy",
            "approximate_kl",
            "clip_fraction",
            "gradient_norm",
        ):
            assert np.isfinite(row[f"{actor}_{metric}"])
    assert 0.0 <= row["E1_active_decision_fraction"] <= 1.0
    assert 0.0 <= row["E2_active_decision_fraction"] <= 1.0
    assert "retailer_orders_mean" in row
    assert "procurement_requirement_mean" in row
    assert "exporter_1_readiness_target_mean" in row


def _diagnostic_rows(rewards):
    return [
        {
            "episode_index": index,
            "episode_seed": episode_scenario_seed(41001, index),
            "scenario_id": f"scenario-{index}",
            "total_team_reward": float(reward),
            "non_finite_event_count": 0,
        }
        for index, reward in enumerate(rewards)
    ]


def test_training_stability_writer_uses_only_locked_1000_episode_budget():
    constant = _diagnostic_rows([-100.0] * TRAINING_EPISODES)
    report = compute_training_stability(constant)
    assert report["training_stable"] is True
    assert report["absolute_relative_mean_change"] == pytest.approx(0.0)
    assert report["final_window_slope"] == pytest.approx(0.0)
    assert report["post_hoc_training_extension_allowed"] is False

    threshold_case = _diagnostic_rows(
        [-100.0] * 800 + [-95.0] * 200
    )
    threshold_report = compute_training_stability(threshold_case)
    assert threshold_report["absolute_relative_mean_change"] == pytest.approx(0.05)
    assert threshold_report["training_stable"] is True

    trending_rewards = [-100.0] * 800 + [
        -100.0 + 0.05 * index for index in range(200)
    ]
    trending = compute_training_stability(_diagnostic_rows(trending_rewards))
    assert trending["training_stable"] is False
    assert not (
        trending["final_window_slope_ci95_low"]
        <= 0.0
        <= trending["final_window_slope_ci95_high"]
    )

    undefined_relative_change = _diagnostic_rows(
        [0.0] * 800 + [1.0] * 200
    )
    undefined_report = compute_training_stability(undefined_relative_change)
    assert undefined_report["absolute_relative_mean_change"] is None
    assert undefined_report["relative_mean_change_defined"] is False
    assert undefined_report["training_stable"] is False

    with pytest.raises(ValueError, match="diagnostic row count"):
        compute_training_stability(constant[:-1])


def test_full_training_gate_requires_explicit_frozen_launcher_sha(monkeypatch):
    monkeypatch.delenv(FULL_TRAINING_AUTH_ENV, raising=False)
    monkeypatch.delenv(FROZEN_LAUNCHER_SHA_ENV, raising=False)
    with pytest.raises(RuntimeError, match="not authorized"):
        require_full_training_authorization(SOURCE_SHA)

    monkeypatch.setenv(FULL_TRAINING_AUTH_ENV, "YES")
    monkeypatch.setenv(FROZEN_LAUNCHER_SHA_ENV, "2" * 40)
    with pytest.raises(RuntimeError, match="frozen launcher SHA"):
        require_full_training_authorization(SOURCE_SHA)

    monkeypatch.setenv(FROZEN_LAUNCHER_SHA_ENV, SOURCE_SHA)
    require_full_training_authorization(SOURCE_SHA)


def test_repository_has_no_hidden_full_training_entrypoint_before_freeze():
    workflow = Path(".github/workflows/ai_launcher_gate.yml").read_text(
        encoding="utf-8"
    )
    assert "run_ai_launcher_dry_run.py" in workflow
    assert "matrix:" not in workflow

    candidate_paths = [
        *Path(".github/workflows").glob("*.yml"),
        *Path(".github/workflows").glob("*.yaml"),
        *Path("scripts").glob("*.py"),
    ]
    for path in candidate_paths:
        text = path.read_text(encoding="utf-8")
        assert "run_locked_training_job" not in text, path
        assert FULL_TRAINING_AUTH_ENV not in text, path
        assert FROZEN_LAUNCHER_SHA_ENV not in text, path
