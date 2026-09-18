from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Iterable

import torch

from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import ExogenousScenario

from .environment import ActorLocalAIDecisionArchitecture
from .training_runner import ACTOR_NAMES


TRAINING_SEEDS = (41001, 41002, 41003, 41004, 41005)
INFORMATION_REGIMES = ("N", "S", "F")
TRAINING_EPISODES = 1000
TRAINING_EPISODE_DAYS = 1000
EVALUATION_MASTER_SEED = 52001

SCENARIO_SEED_PROTOCOL_VERSION = "training-scenario-sha256-v0.1"
CHECKPOINT_VERSION = "ai-training-checkpoint-v0.1"
RUNNER_PROTOCOL_VERSION = "ai-full-training-v0.1"
FROZEN_SMOKE_BASE = "dadfec406647065a2055d31b5bbbc404c2dbefe6"
AI_SPEC_BASE = "2af1c2f6e6f52c65576e00a33de65942bddd3c92"


def _canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def simulation_config_payload(config: SimulationConfig) -> dict:
    config.validate()
    payload = asdict(config)
    payload["retailer_mean_demand"] = list(config.retailer_mean_demand)
    payload["exporter_availability_probability"] = list(
        config.exporter_availability_probability
    )
    return payload


def simulation_config_hash(config: SimulationConfig) -> str:
    return hashlib.sha256(
        _canonical_json(simulation_config_payload(config)).encode("utf-8")
    ).hexdigest()


def _validate_training_seed(training_seed: int) -> int:
    seed = int(training_seed)
    if seed not in TRAINING_SEEDS:
        raise ValueError(
            f"training_seed must be one of the pre-registered seeds {TRAINING_SEEDS}"
        )
    if seed == EVALUATION_MASTER_SEED:
        raise ValueError("evaluation master seed is reserved and cannot train")
    return seed


def _validate_episode_index(episode_index: int) -> int:
    index = int(episode_index)
    if not 0 <= index < TRAINING_EPISODES:
        raise ValueError(
            f"episode_index must lie in [0, {TRAINING_EPISODES - 1}]"
        )
    return index


def episode_scenario_seed(training_seed: int, episode_index: int) -> int:
    """Domain-separated deterministic training scenario seed.

    The regime is deliberately absent from this mapping, which makes the
    exogenous episode stream common across N/S/F for a fixed training seed and
    episode index.
    """
    seed = _validate_training_seed(training_seed)
    index = _validate_episode_index(episode_index)
    payload = (
        f"{SCENARIO_SEED_PROTOCOL_VERSION}|training|{seed}|episode|{index}"
    ).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    candidate = int.from_bytes(digest[:8], "big") % (2**32 - 1)

    # Reserve the evaluation master seed even under accidental hash collision.
    if candidate == EVALUATION_MASTER_SEED:
        digest = hashlib.sha256(digest + b"|reserved-eval-seed-rehash").digest()
        candidate = int.from_bytes(digest[:8], "big") % (2**32 - 1)
        if candidate == EVALUATION_MASTER_SEED:
            raise AssertionError("failed to domain-separate training seed stream")
    return int(candidate)


def episode_seed_schedule(
    training_seed: int,
    episode_count: int = TRAINING_EPISODES,
) -> tuple[int, ...]:
    count = int(episode_count)
    if not 1 <= count <= TRAINING_EPISODES:
        raise ValueError(
            f"episode_count must lie in [1, {TRAINING_EPISODES}]"
        )
    return tuple(
        episode_scenario_seed(training_seed, episode_index)
        for episode_index in range(count)
    )


def episode_manifest_record(
    *,
    training_seed: int,
    episode_index: int,
    scenario: ExogenousScenario,
) -> dict:
    expected_seed = episode_scenario_seed(training_seed, episode_index)
    if int(scenario.replication_seed) != expected_seed:
        raise ValueError(
            "scenario replication seed does not match the locked training schedule"
        )
    if not scenario.scenario_id:
        raise ValueError("scenario_id must be non-empty")
    return {
        "episode_index": int(episode_index),
        "episode_seed": int(expected_seed),
        "scenario_id": str(scenario.scenario_id),
    }


def build_run_manifest(
    *,
    regime: str,
    training_seed: int,
    config: SimulationConfig,
    episode_records: Iterable[dict] = (),
) -> dict:
    if regime not in INFORMATION_REGIMES:
        raise ValueError(f"regime must be one of {INFORMATION_REGIMES}")
    seed = _validate_training_seed(training_seed)
    config.validate()
    if config.simulation_horizon_days != TRAINING_EPISODE_DAYS:
        raise ValueError(
            "scientific training manifest requires exactly 1000 days per episode"
        )

    records = [dict(record) for record in episode_records]
    manifest = {
        "runner_protocol_version": RUNNER_PROTOCOL_VERSION,
        "checkpoint_version": CHECKPOINT_VERSION,
        "scenario_seed_protocol_version": SCENARIO_SEED_PROTOCOL_VERSION,
        "frozen_smoke_base": FROZEN_SMOKE_BASE,
        "ai_spec_base": AI_SPEC_BASE,
        "regime": regime,
        "training_seed": seed,
        "pre_registered_training_seeds": list(TRAINING_SEEDS),
        "pre_registered_regimes": list(INFORMATION_REGIMES),
        "episode_budget": TRAINING_EPISODES,
        "episode_horizon_days": TRAINING_EPISODE_DAYS,
        "rollout_length_days": 256,
        "evaluation_master_seed_reserved": EVALUATION_MASTER_SEED,
        "simulation_config": simulation_config_payload(config),
        "simulation_config_sha256": simulation_config_hash(config),
        "completed_episode_count": len(records),
        "episodes": records,
    }
    validate_run_manifest(manifest)
    return manifest


def validate_run_manifest(manifest: dict) -> None:
    required = {
        "runner_protocol_version",
        "checkpoint_version",
        "scenario_seed_protocol_version",
        "frozen_smoke_base",
        "ai_spec_base",
        "regime",
        "training_seed",
        "pre_registered_training_seeds",
        "pre_registered_regimes",
        "episode_budget",
        "episode_horizon_days",
        "rollout_length_days",
        "evaluation_master_seed_reserved",
        "simulation_config",
        "simulation_config_sha256",
        "completed_episode_count",
        "episodes",
    }
    missing = required.difference(manifest)
    if missing:
        raise ValueError(f"manifest missing fields: {sorted(missing)}")
    if manifest["runner_protocol_version"] != RUNNER_PROTOCOL_VERSION:
        raise ValueError("runner protocol version drift")
    if manifest["checkpoint_version"] != CHECKPOINT_VERSION:
        raise ValueError("checkpoint version drift")
    if manifest["scenario_seed_protocol_version"] != SCENARIO_SEED_PROTOCOL_VERSION:
        raise ValueError("scenario seed protocol version drift")
    if manifest["regime"] not in INFORMATION_REGIMES:
        raise ValueError("invalid manifest regime")
    seed = _validate_training_seed(int(manifest["training_seed"]))
    if int(manifest["episode_budget"]) != TRAINING_EPISODES:
        raise ValueError("training episode budget drift")
    if int(manifest["episode_horizon_days"]) != TRAINING_EPISODE_DAYS:
        raise ValueError("episode horizon drift")
    if int(manifest["rollout_length_days"]) != 256:
        raise ValueError("rollout length drift")
    if int(manifest["evaluation_master_seed_reserved"]) != EVALUATION_MASTER_SEED:
        raise ValueError("evaluation-seed reservation drift")

    expected_config_hash = hashlib.sha256(
        _canonical_json(manifest["simulation_config"]).encode("utf-8")
    ).hexdigest()
    if manifest["simulation_config_sha256"] != expected_config_hash:
        raise ValueError("manifest simulation config hash mismatch")

    episodes = manifest["episodes"]
    if not isinstance(episodes, list):
        raise ValueError("manifest episodes must be a list")
    if int(manifest["completed_episode_count"]) != len(episodes):
        raise ValueError("completed episode count does not match manifest rows")
    if len(episodes) > TRAINING_EPISODES:
        raise ValueError("manifest exceeds the pre-registered episode budget")

    for expected_index, record in enumerate(episodes):
        if set(record) != {"episode_index", "episode_seed", "scenario_id"}:
            raise ValueError("invalid episode manifest record")
        if int(record["episode_index"]) != expected_index:
            raise ValueError("episode manifest indices must be contiguous from zero")
        expected_seed = episode_scenario_seed(seed, expected_index)
        if int(record["episode_seed"]) != expected_seed:
            raise ValueError("episode manifest seed violates the locked schedule")
        if int(record["episode_seed"]) == EVALUATION_MASTER_SEED:
            raise ValueError("evaluation master seed contaminated training manifest")
        if not str(record["scenario_id"]):
            raise ValueError("episode scenario_id must be non-empty")


def _iter_optimizer_tensors(value):
    if isinstance(value, torch.Tensor):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _iter_optimizer_tensors(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _iter_optimizer_tensors(child)


def validate_finite_training_state(
    architecture: ActorLocalAIDecisionArchitecture,
) -> None:
    if set(architecture.agents) != set(ACTOR_NAMES):
        raise ValueError("checkpoint architecture does not contain all six actors")

    for actor_name in ACTOR_NAMES:
        agent = architecture.agents[actor_name]
        for parameter in agent.network.parameters():
            if not torch.isfinite(parameter.detach()).all():
                raise FloatingPointError(
                    f"{actor_name} network contains non-finite parameters"
                )
        optimizer_state = agent.updater.optimizer.state_dict()
        for tensor in _iter_optimizer_tensors(optimizer_state):
            if tensor.is_floating_point() or tensor.is_complex():
                if not torch.isfinite(tensor).all():
                    raise FloatingPointError(
                        f"{actor_name} optimizer contains non-finite state"
                    )


def checkpoint_payload(
    *,
    architecture: ActorLocalAIDecisionArchitecture,
    regime: str,
    completed_episode_count: int,
    config: SimulationConfig,
) -> dict:
    if regime not in INFORMATION_REGIMES:
        raise ValueError(f"regime must be one of {INFORMATION_REGIMES}")
    seed = _validate_training_seed(architecture.training_seed)
    completed = int(completed_episode_count)
    if not 0 <= completed <= TRAINING_EPISODES:
        raise ValueError("invalid completed_episode_count")
    validate_finite_training_state(architecture)

    return {
        "checkpoint_version": CHECKPOINT_VERSION,
        "runner_protocol_version": RUNNER_PROTOCOL_VERSION,
        "scenario_seed_protocol_version": SCENARIO_SEED_PROTOCOL_VERSION,
        "frozen_smoke_base": FROZEN_SMOKE_BASE,
        "ai_spec_base": AI_SPEC_BASE,
        "regime": regime,
        "training_seed": seed,
        "completed_episode_count": completed,
        "simulation_config": simulation_config_payload(config),
        "simulation_config_sha256": simulation_config_hash(config),
        "actors": {
            actor_name: architecture.agents[actor_name].checkpoint_state()
            for actor_name in ACTOR_NAMES
        },
    }


def save_training_checkpoint(
    path: str | Path,
    *,
    architecture: ActorLocalAIDecisionArchitecture,
    regime: str,
    completed_episode_count: int,
    config: SimulationConfig,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = checkpoint_payload(
        architecture=architecture,
        regime=regime,
        completed_episode_count=completed_episode_count,
        config=config,
    )
    torch.save(payload, destination)
    return destination


def load_training_checkpoint(
    path: str | Path,
    *,
    config: SimulationConfig,
    expected_regime: str,
    expected_training_seed: int,
    device: str | torch.device = "cpu",
) -> tuple[ActorLocalAIDecisionArchitecture, dict]:
    payload = torch.load(
        Path(path),
        map_location=torch.device(device),
        weights_only=False,
    )
    if not isinstance(payload, dict):
        raise ValueError("training checkpoint must contain a dictionary payload")
    required = {
        "checkpoint_version",
        "runner_protocol_version",
        "scenario_seed_protocol_version",
        "frozen_smoke_base",
        "ai_spec_base",
        "regime",
        "training_seed",
        "completed_episode_count",
        "simulation_config",
        "simulation_config_sha256",
        "actors",
    }
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"checkpoint missing fields: {sorted(missing)}")
    if payload["checkpoint_version"] != CHECKPOINT_VERSION:
        raise ValueError("checkpoint version mismatch")
    if payload["runner_protocol_version"] != RUNNER_PROTOCOL_VERSION:
        raise ValueError("runner protocol version mismatch")
    if payload["scenario_seed_protocol_version"] != SCENARIO_SEED_PROTOCOL_VERSION:
        raise ValueError("scenario seed protocol version mismatch")
    if payload["frozen_smoke_base"] != FROZEN_SMOKE_BASE:
        raise ValueError("frozen smoke base mismatch")
    if payload["ai_spec_base"] != AI_SPEC_BASE:
        raise ValueError("AI specification base mismatch")
    if payload["regime"] != expected_regime:
        raise ValueError("checkpoint regime does not match requested resume regime")
    expected_seed = _validate_training_seed(expected_training_seed)
    if int(payload["training_seed"]) != expected_seed:
        raise ValueError("checkpoint training seed does not match requested resume seed")
    if payload["simulation_config_sha256"] != simulation_config_hash(config):
        raise ValueError("checkpoint simulation config does not match resume config")
    if set(payload["actors"]) != set(ACTOR_NAMES):
        raise ValueError("checkpoint must contain exactly six actor states")

    architecture = ActorLocalAIDecisionArchitecture(
        config,
        training_seed=expected_seed,
        deterministic=False,
        device=device,
    )
    for actor_name in ACTOR_NAMES:
        architecture.agents[actor_name].load_checkpoint_state(
            payload["actors"][actor_name]
        )
    validate_finite_training_state(architecture)
    return architecture, {
        "checkpoint_version": payload["checkpoint_version"],
        "runner_protocol_version": payload["runner_protocol_version"],
        "scenario_seed_protocol_version": payload[
            "scenario_seed_protocol_version"
        ],
        "regime": payload["regime"],
        "training_seed": int(payload["training_seed"]),
        "completed_episode_count": int(payload["completed_episode_count"]),
        "simulation_config_sha256": payload["simulation_config_sha256"],
    }
