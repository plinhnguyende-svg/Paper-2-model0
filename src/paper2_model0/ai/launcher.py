from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import torch

from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import generate_scenario

from .environment import (
    ActorLocalAIDecisionArchitecture,
    physical_team_rewards,
)
from .training_protocol import (
    INFORMATION_REGIMES,
    TRAINING_EPISODE_DAYS,
    TRAINING_EPISODES,
    TRAINING_SEEDS,
    build_run_manifest,
    episode_manifest_record,
    episode_scenario_seed,
    load_training_checkpoint,
    run_manifest_hash,
    save_training_checkpoint,
    simulation_config_hash,
    training_run_keys,
    validate_run_manifest,
    validate_scientific_training_contract,
)
from .training_runner import ACTOR_NAMES, BoundaryAwareEpisodeRunner, BoundaryTrainingResult


LAUNCHER_PROTOCOL_VERSION = "ai-15run-launcher-v0.1"
FROZEN_RUNNER_BASE = "d310ad960a410d03b87b123dfdc45b2bbf45946d"
LOCKED_TRAINING_DEVICE = "cpu"
FULL_TRAINING_AUTH_ENV = "PAPER2_AI_FULL_TRAINING_AUTHORIZED"
FROZEN_LAUNCHER_SHA_ENV = "PAPER2_AI_FROZEN_LAUNCHER_SHA"

_EXPECTED_RUN_KEYS = tuple(
    (regime, seed)
    for regime in ("N", "S", "F")
    for seed in (41001, 41002, 41003, 41004, 41005)
)


@dataclass(frozen=True)
class LauncherJob:
    regime: str
    training_seed: int

    @property
    def job_id(self) -> str:
        return f"{self.regime}-seed-{self.training_seed}"

    @property
    def relative_directory(self) -> Path:
        return Path(f"regime_{self.regime}") / f"seed_{self.training_seed}"


@dataclass(frozen=True)
class LauncherResumeState:
    job: LauncherJob
    architecture: ActorLocalAIDecisionArchitecture
    manifest: dict
    diagnostics: tuple[dict, ...]
    next_episode_index: int


def validate_launcher_device(device: str | torch.device) -> None:
    if str(torch.device(device)) != LOCKED_TRAINING_DEVICE:
        raise ValueError("confirmatory launcher is locked to CPU execution")


def locked_simulation_config() -> SimulationConfig:
    """Return the exact baseline SimulationConfig for confirmatory AI training."""
    return SimulationConfig()


def validate_launcher_config(config: SimulationConfig) -> None:
    config.validate()
    expected = locked_simulation_config()
    if config != expected:
        raise ValueError(
            "15-run confirmatory launcher requires the exact locked "
            "SimulationConfig baseline"
        )


def locked_job_registry() -> tuple[LauncherJob, ...]:
    frozen_keys = training_run_keys()
    if frozen_keys != _EXPECTED_RUN_KEYS:
        raise AssertionError("frozen runner 15-job registry drift")
    jobs = tuple(LauncherJob(regime, seed) for regime, seed in frozen_keys)
    if len(jobs) != 15 or len({job.job_id for job in jobs}) != 15:
        raise AssertionError("launcher registry must contain 15 unique jobs")
    return jobs


def locked_job(regime: str, training_seed: int) -> LauncherJob:
    key = (str(regime), int(training_seed))
    if key not in _EXPECTED_RUN_KEYS:
        raise ValueError("launcher accepts only a pre-registered regime/seed pair")
    return LauncherJob(*key)


def build_dry_run_contract() -> dict:
    """Describe the exact 15 jobs without constructing or training any agent."""
    config = locked_simulation_config()
    validate_launcher_config(config)
    jobs = []
    for job in locked_job_registry():
        jobs.append(
            {
                "job_id": job.job_id,
                "regime": job.regime,
                "training_seed": job.training_seed,
                "relative_directory": job.relative_directory.as_posix(),
                "episode_count": TRAINING_EPISODES,
                "episode_horizon_days": TRAINING_EPISODE_DAYS,
                "first_episode_seed": episode_scenario_seed(job.training_seed, 0),
                "last_episode_seed": episode_scenario_seed(
                    job.training_seed, TRAINING_EPISODES - 1
                ),
            }
        )
    return {
        "launcher_protocol_version": LAUNCHER_PROTOCOL_VERSION,
        "frozen_runner_base": FROZEN_RUNNER_BASE,
        "job_count": len(jobs),
        "episode_count_per_job": TRAINING_EPISODES,
        "episode_horizon_days": TRAINING_EPISODE_DAYS,
        "simulation_config_sha256": simulation_config_hash(config),
        "locked_training_device": LOCKED_TRAINING_DEVICE,
        "jobs": jobs,
        "full_training_authorized": False,
    }


def require_full_training_authorization(source_commit_sha: str) -> None:
    """Require an explicit post-freeze authorization without changing code."""
    source = str(source_commit_sha).strip().lower()
    if os.environ.get(FULL_TRAINING_AUTH_ENV) != "YES":
        raise RuntimeError(
            "full scientific training is not authorized; launcher remains "
            "in dry-run/test gate"
        )
    frozen = os.environ.get(FROZEN_LAUNCHER_SHA_ENV, "").strip().lower()
    if frozen != source:
        raise RuntimeError(
            "full scientific training requires source_commit_sha to match "
            "the explicitly frozen launcher SHA"
        )


def build_launcher_manifest(
    *,
    job: LauncherJob,
    config: SimulationConfig,
    source_commit_sha: str,
    episode_records: Iterable[dict] = (),
) -> dict:
    validate_launcher_config(config)
    if job not in locked_job_registry():
        raise ValueError("job is not in the frozen 15-run registry")
    manifest = build_run_manifest(
        regime=job.regime,
        training_seed=job.training_seed,
        config=config,
        source_commit_sha=source_commit_sha,
        episode_records=episode_records,
    )
    manifest["launcher_protocol_version"] = LAUNCHER_PROTOCOL_VERSION
    manifest["frozen_runner_base"] = FROZEN_RUNNER_BASE
    manifest["launcher_job_id"] = job.job_id
    manifest["locked_training_device"] = LOCKED_TRAINING_DEVICE
    validate_launcher_manifest(manifest)
    return manifest


def validate_launcher_manifest(manifest: dict) -> None:
    validate_run_manifest(manifest)
    if manifest.get("launcher_protocol_version") != LAUNCHER_PROTOCOL_VERSION:
        raise ValueError("launcher protocol version drift")
    if manifest.get("frozen_runner_base") != FROZEN_RUNNER_BASE:
        raise ValueError("frozen runner base drift")
    job = locked_job(manifest["regime"], int(manifest["training_seed"]))
    if manifest.get("launcher_job_id") != job.job_id:
        raise ValueError("launcher manifest job id mismatch")
    if manifest.get("locked_training_device") != LOCKED_TRAINING_DEVICE:
        raise ValueError("launcher training device drift")
    if manifest["simulation_config_sha256"] != simulation_config_hash(
        locked_simulation_config()
    ):
        raise ValueError("launcher manifest does not use the locked baseline config")


def _atomic_write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(
        json.dumps(value, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, path)


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _atomic_write_diagnostics(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    pd.DataFrame(rows).to_csv(temp, index=False)
    os.replace(temp, path)


def _read_diagnostics(path: Path) -> list[dict]:
    if not path.exists():
        return []
    frame = pd.read_csv(path)
    if len(frame) == 0:
        return []
    return frame.to_dict(orient="records")


def _validate_diagnostic_rows(rows: list[dict], completed_count: int) -> None:
    if len(rows) != completed_count:
        raise ValueError("diagnostic row count does not match completed episodes")
    for expected_index, row in enumerate(rows):
        if int(row.get("episode_index", -1)) != expected_index:
            raise ValueError("diagnostic episode indices must be contiguous from zero")
        if not str(row.get("scenario_id", "")):
            raise ValueError("diagnostic scenario_id must be non-empty")
        if not math.isfinite(float(row.get("total_team_reward", float("nan")))):
            raise ValueError("diagnostic total_team_reward must be finite")
        if int(row.get("non_finite_event_count", -1)) != 0:
            raise ValueError("successful episode diagnostics require zero non-finite events")


def _episode_file_count(path: Path) -> int | None:
    stem = path.stem
    if "_episode_" not in stem:
        return None
    suffix = stem.rsplit("_episode_", 1)[1]
    try:
        return int(suffix)
    except ValueError:
        return None


class LauncherRunStore:
    """Crash-safe episode-boundary store.

    The latest pointer is replaced only after manifest, checkpoint, and
    diagnostics are durable. If a process dies before that final pointer swap,
    the next resume removes higher-count orphan files and resumes from the
    previously committed episode boundary.
    """

    def __init__(self, output_root: str | Path, job: LauncherJob):
        if job not in locked_job_registry():
            raise ValueError("run store requires a frozen launcher job")
        self.output_root = Path(output_root)
        self.job = job
        self.job_dir = self.output_root / job.relative_directory
        self.state_dir = self.job_dir / "state"
        self.diagnostics_path = self.job_dir / "diagnostics" / "episodes.csv"
        self.stability_path = self.job_dir / "diagnostics" / "stability.json"
        self.latest_path = self.state_dir / "latest.json"

    def manifest_path(self, completed_count: int) -> Path:
        return self.state_dir / f"manifest_episode_{int(completed_count):04d}.json"

    def checkpoint_path(self, completed_count: int) -> Path:
        return self.state_dir / f"checkpoint_episode_{int(completed_count):04d}.pt"

    def initialize(self, manifest: dict) -> None:
        validate_launcher_manifest(manifest)
        if int(manifest["completed_episode_count"]) != 0:
            raise ValueError("initial launcher manifest must precede episode 0")
        if self.latest_path.exists():
            raise FileExistsError("launcher job is already initialized")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.manifest_path(0)
        _atomic_write_json(manifest_path, manifest)
        _atomic_write_json(
            self.latest_path,
            {
                "completed_episode_count": 0,
                "manifest_file": manifest_path.name,
                "checkpoint_file": None,
                "run_manifest_sha256": run_manifest_hash(manifest),
            },
        )

    def _latest_pointer(self) -> dict:
        if not self.latest_path.exists():
            raise FileNotFoundError("launcher latest pointer does not exist")
        pointer = _read_json(self.latest_path)
        required = {
            "completed_episode_count",
            "manifest_file",
            "checkpoint_file",
            "run_manifest_sha256",
        }
        if set(pointer) != required:
            raise ValueError("invalid launcher latest pointer")
        completed = int(pointer["completed_episode_count"])
        if not 0 <= completed <= TRAINING_EPISODES:
            raise ValueError("latest pointer episode count is outside locked budget")
        return pointer

    def _recover_orphans(self, committed_count: int) -> None:
        if self.state_dir.exists():
            for path in self.state_dir.iterdir():
                count = _episode_file_count(path)
                if count is not None and count > committed_count:
                    path.unlink(missing_ok=True)

        rows = _read_diagnostics(self.diagnostics_path)
        if rows:
            committed_rows = [
                row for row in rows
                if int(row.get("episode_index", -1)) < committed_count
            ]
            if len(committed_rows) < committed_count:
                raise ValueError(
                    "diagnostics are behind the committed launcher pointer"
                )
            if len(committed_rows) != len(rows):
                _validate_diagnostic_rows(committed_rows, committed_count)
                _atomic_write_diagnostics(self.diagnostics_path, committed_rows)
        elif committed_count:
            raise ValueError("committed launcher state is missing diagnostics")

        if committed_count < TRAINING_EPISODES and self.stability_path.exists():
            self.stability_path.unlink()

    def load_committed_state(
        self,
        *,
        config: SimulationConfig,
        source_commit_sha: str,
        device: str | torch.device = "cpu",
    ) -> LauncherResumeState:
        validate_launcher_config(config)
        pointer = self._latest_pointer()
        completed = int(pointer["completed_episode_count"])
        self._recover_orphans(completed)

        manifest_path = self.state_dir / str(pointer["manifest_file"])
        manifest = _read_json(manifest_path)
        validate_launcher_manifest(manifest)
        if manifest["regime"] != self.job.regime:
            raise ValueError("resume manifest regime does not match launcher job")
        if int(manifest["training_seed"]) != self.job.training_seed:
            raise ValueError("resume manifest training seed does not match launcher job")
        if manifest["source_commit_sha"] != str(source_commit_sha).strip().lower():
            raise ValueError("resume source commit differs from initialized run")
        if int(manifest["completed_episode_count"]) != completed:
            raise ValueError("latest pointer and manifest episode counts differ")
        if run_manifest_hash(manifest) != pointer["run_manifest_sha256"]:
            raise ValueError("latest pointer manifest hash mismatch")

        diagnostics = _read_diagnostics(self.diagnostics_path)
        _validate_diagnostic_rows(diagnostics, completed)

        if completed == 0:
            if pointer["checkpoint_file"] is not None:
                raise ValueError("episode-zero pointer must not carry a checkpoint")
            architecture = ActorLocalAIDecisionArchitecture(
                config,
                training_seed=self.job.training_seed,
                deterministic=False,
                device=device,
            )
        else:
            checkpoint_name = pointer["checkpoint_file"]
            if not checkpoint_name:
                raise ValueError("committed episode state is missing checkpoint file")
            architecture, metadata = load_training_checkpoint(
                self.state_dir / str(checkpoint_name),
                config=config,
                expected_regime=self.job.regime,
                expected_training_seed=self.job.training_seed,
                expected_manifest=manifest,
                device=device,
            )
            if int(metadata["completed_episode_count"]) != completed:
                raise ValueError("checkpoint episode count differs from pointer")

        return LauncherResumeState(
            job=self.job,
            architecture=architecture,
            manifest=manifest,
            diagnostics=tuple(diagnostics),
            next_episode_index=completed,
        )

    def commit_episode_boundary(
        self,
        *,
        config: SimulationConfig,
        architecture: ActorLocalAIDecisionArchitecture,
        manifest: dict,
        diagnostics: list[dict],
    ) -> None:
        validate_launcher_config(config)
        validate_launcher_manifest(manifest)
        completed = int(manifest["completed_episode_count"])
        if not 1 <= completed <= TRAINING_EPISODES:
            raise ValueError("episode-boundary commit count is outside locked budget")
        _validate_diagnostic_rows(diagnostics, completed)

        pointer = self._latest_pointer()
        previous = int(pointer["completed_episode_count"])
        if completed != previous + 1:
            raise ValueError("launcher may commit only the exact next episode")

        manifest_path = self.manifest_path(completed)
        checkpoint_path = self.checkpoint_path(completed)
        if manifest_path.exists() or checkpoint_path.exists():
            raise FileExistsError("episode boundary already exists; replay is forbidden")

        self.state_dir.mkdir(parents=True, exist_ok=True)
        manifest_temp = manifest_path.with_name(manifest_path.name + ".tmp")
        checkpoint_temp = checkpoint_path.with_name(checkpoint_path.name + ".tmp")
        diagnostics_temp = self.diagnostics_path.with_name(
            self.diagnostics_path.name + ".tmp"
        )
        self.diagnostics_path.parent.mkdir(parents=True, exist_ok=True)

        manifest_temp.write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        save_training_checkpoint(
            checkpoint_temp,
            architecture=architecture,
            regime=self.job.regime,
            completed_episode_count=completed,
            config=config,
            manifest=manifest,
        )
        pd.DataFrame(diagnostics).to_csv(diagnostics_temp, index=False)

        os.replace(manifest_temp, manifest_path)
        os.replace(checkpoint_temp, checkpoint_path)
        os.replace(diagnostics_temp, self.diagnostics_path)

        _atomic_write_json(
            self.latest_path,
            {
                "completed_episode_count": completed,
                "manifest_file": manifest_path.name,
                "checkpoint_file": checkpoint_path.name,
                "run_manifest_sha256": run_manifest_hash(manifest),
            },
        )
        self._prune_old_state(completed)

    def _prune_old_state(self, committed_count: int) -> None:
        keep_from = max(0, committed_count - 1)
        for path in self.state_dir.iterdir():
            count = _episode_file_count(path)
            if count is not None and count < keep_from:
                path.unlink(missing_ok=True)

    def write_stability_report(self, report: dict) -> None:
        _atomic_write_json(self.stability_path, report)


def load_or_initialize_locked_job(
    *,
    output_root: str | Path,
    job: LauncherJob,
    source_commit_sha: str,
    config: SimulationConfig | None = None,
    device: str | torch.device = "cpu",
) -> LauncherResumeState:
    config = config or locked_simulation_config()
    validate_launcher_config(config)
    validate_launcher_device(device)
    validate_scientific_training_contract(
        regime=job.regime,
        training_seed=job.training_seed,
        config=config,
    )
    store = LauncherRunStore(output_root, job)
    if not store.latest_path.exists():
        manifest = build_launcher_manifest(
            job=job,
            config=config,
            source_commit_sha=source_commit_sha,
        )
        store.initialize(manifest)
    return store.load_committed_state(
        config=config,
        source_commit_sha=source_commit_sha,
        device=device,
    )


def _weighted_update_mean(events, attribute: str) -> float:
    weights = np.asarray(
        [max(1, int(event.stats.minibatch_updates)) for event in events],
        dtype=float,
    )
    values = np.asarray(
        [float(getattr(event.stats, attribute)) for event in events],
        dtype=float,
    )
    if len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("episode update diagnostics contain invalid values")
    return float(np.average(values, weights=weights))


def _series_summary(frame: pd.DataFrame, column: str, prefix: str) -> dict:
    values = frame[column].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"non-finite transformed action summary in {column}")
    return {
        f"{prefix}_mean": float(values.mean()),
        f"{prefix}_std": float(values.std(ddof=0)),
        f"{prefix}_min": float(values.min()),
        f"{prefix}_max": float(values.max()),
    }


def episode_diagnostics(
    *,
    result: BoundaryTrainingResult,
    architecture: ActorLocalAIDecisionArchitecture,
    episode_index: int,
    episode_seed: int,
) -> dict:
    frame = result.period_df
    rewards = physical_team_rewards(
        frame,
        aggregate_mean_demand=architecture.encoder.aggregate_mean_demand,
    )
    row: dict[str, object] = {
        "episode_index": int(episode_index),
        "episode_seed": int(episode_seed),
        "scenario_id": str(result.scenario_id),
        "total_team_reward": float(rewards.sum()),
        "non_finite_event_count": 0,
    }

    for actor in ACTOR_NAMES:
        events = [event for event in result.update_events if event.actor == actor]
        if not events:
            raise ValueError(f"{actor} produced no PPO update event")
        for attribute in (
            "policy_loss",
            "value_loss",
            "entropy",
            "total_loss",
            "approximate_kl",
            "clip_fraction",
            "gradient_norm",
        ):
            row[f"{actor}_{attribute}"] = _weighted_update_mean(
                events, attribute
            )

    for column, prefix in (
        ("aggregate_retailer_orders", "retailer_orders"),
        ("procurement_requirement", "procurement_requirement"),
        ("readiness_target_1", "exporter_1_readiness_target"),
        ("readiness_target_2", "exporter_2_readiness_target"),
        ("prepared_quantity_1", "exporter_1_prepared_quantity"),
        ("prepared_quantity_2", "exporter_2_prepared_quantity"),
    ):
        row.update(_series_summary(frame, column, prefix))

    records = architecture.records_by_actor()
    for actor in ("E1", "E2"):
        actor_records = records[actor]
        if len(actor_records) != len(frame):
            raise ValueError(f"{actor} diagnostic trace length mismatch")
        row[f"{actor}_active_decision_fraction"] = float(
            np.mean([record.policy_active for record in actor_records])
        )

    numeric_values = [
        float(value)
        for key, value in row.items()
        if key not in {"scenario_id"} and isinstance(value, (int, float, np.number))
    ]
    if not np.isfinite(np.asarray(numeric_values, dtype=float)).all():
        raise ValueError("episode diagnostics contain non-finite values")
    return row


def compute_training_stability(diagnostics: Iterable[dict]) -> dict:
    rows = list(diagnostics)
    _validate_diagnostic_rows(rows, TRAINING_EPISODES)
    rewards = np.asarray(
        [float(row["total_team_reward"]) for row in rows],
        dtype=float,
    )
    earlier = rewards[600:800]
    final = rewards[800:1000]
    earlier_mean = float(earlier.mean())
    final_mean = float(final.mean())

    if earlier_mean == 0.0:
        relative_change = 0.0 if final_mean == 0.0 else float("inf")
    else:
        relative_change = abs((final_mean - earlier_mean) / earlier_mean)

    x = np.arange(801.0, 1001.0, dtype=float)
    centered_x = x - x.mean()
    centered_y = final - final.mean()
    sxx = float(np.dot(centered_x, centered_x))
    slope = float(np.dot(centered_x, centered_y) / sxx)
    intercept = float(final.mean() - slope * x.mean())
    residual = final - (intercept + slope * x)
    residual_variance = float(np.dot(residual, residual) / (len(final) - 2))
    slope_standard_error = math.sqrt(max(0.0, residual_variance / sxx))
    ci_half_width = 1.96 * slope_standard_error
    ci_low = slope - ci_half_width
    ci_high = slope + ci_half_width

    stable = bool(
        relative_change <= 0.05
        and ci_low <= 0.0 <= ci_high
    )
    return {
        "launcher_protocol_version": LAUNCHER_PROTOCOL_VERSION,
        "episode_count": TRAINING_EPISODES,
        "mean_reward_episodes_601_800": earlier_mean,
        "mean_reward_episodes_801_1000": final_mean,
        "absolute_relative_mean_change": relative_change,
        "relative_mean_change_threshold": 0.05,
        "final_window_slope": slope,
        "final_window_slope_standard_error": slope_standard_error,
        "final_window_slope_ci95_low": ci_low,
        "final_window_slope_ci95_high": ci_high,
        "slope_ci_method": "OLS normal approximation: slope +/- 1.96 standard errors",
        "training_stable": stable,
        "label": (
            "training-stable"
            if stable
            else "not stabilized under the pre-registered budget"
        ),
        "post_hoc_training_extension_allowed": False,
    }


def run_locked_training_job(
    *,
    output_root: str | Path,
    job: LauncherJob,
    source_commit_sha: str,
) -> dict:
    """Run exactly one frozen scientific job after an explicit freeze gate.

    There is intentionally no episode-count, regime, seed, config, or PPO
    override argument. The 15-job workflow is not part of this PR.
    """
    require_full_training_authorization(source_commit_sha)
    config = locked_simulation_config()
    device = LOCKED_TRAINING_DEVICE
    state = load_or_initialize_locked_job(
        output_root=output_root,
        job=job,
        source_commit_sha=source_commit_sha,
        config=config,
        device=device,
    )
    store = LauncherRunStore(output_root, job)
    architecture = state.architecture
    manifest = state.manifest
    diagnostics = list(state.diagnostics)

    for episode_index in range(state.next_episode_index, TRAINING_EPISODES):
        episode_seed = episode_scenario_seed(job.training_seed, episode_index)
        scenario = generate_scenario(config, episode_seed)
        result = BoundaryAwareEpisodeRunner(
            config=config,
            regime=job.regime,
            scenario=scenario,
            training_seed=job.training_seed,
            architecture=architecture,
            device=device,
        ).run_episode()

        record = episode_manifest_record(
            training_seed=job.training_seed,
            episode_index=episode_index,
            scenario=scenario,
        )
        manifest = build_launcher_manifest(
            job=job,
            config=config,
            source_commit_sha=source_commit_sha,
            episode_records=[*manifest["episodes"], record],
        )
        diagnostics.append(
            episode_diagnostics(
                result=result,
                architecture=architecture,
                episode_index=episode_index,
                episode_seed=episode_seed,
            )
        )
        store.commit_episode_boundary(
            config=config,
            architecture=architecture,
            manifest=manifest,
            diagnostics=diagnostics,
        )

    report = compute_training_stability(diagnostics)
    report.update(
        {
            "job_id": job.job_id,
            "regime": job.regime,
            "training_seed": job.training_seed,
            "source_commit_sha": str(source_commit_sha).strip().lower(),
            "frozen_runner_base": FROZEN_RUNNER_BASE,
            "final_manifest_sha256": run_manifest_hash(manifest),
            "final_checkpoint_file": store.checkpoint_path(
                TRAINING_EPISODES
            ).name,
        }
    )
    store.write_stability_report(report)
    return report
