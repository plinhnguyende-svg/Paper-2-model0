from .encoders import AIObservationEncoder
from .forecast import FixedForecastTransitionAdapter
from .transforms import BoundedActionTransformer, stable_sigmoid


__all__ = [
    "AIObservationEncoder",
    "BoundedActionTransformer",
    "FixedForecastTransitionAdapter",
    "stable_sigmoid",
]

from .agents import ActorLocalIPPOAgent, build_actor_local_ippo_agents
from .networks import ACTOR_NETWORK_SPECS, ActorNetworkSpec, GaussianActorCritic
from .ppo import (
    ActorRolloutBuffer,
    PPOHyperparameters,
    PPOTrainingBatch,
    PPOUpdateStats,
    PPOUpdater,
    compute_gae,
)

__all__ += [
    "ACTOR_NETWORK_SPECS",
    "ActorLocalIPPOAgent",
    "ActorNetworkSpec",
    "ActorRolloutBuffer",
    "GaussianActorCritic",
    "PPOHyperparameters",
    "PPOTrainingBatch",
    "PPOUpdateStats",
    "PPOUpdater",
    "build_actor_local_ippo_agents",
    "compute_gae",
]

from .environment import (
    ActorLocalAIDecisionArchitecture,
    DecisionRecord,
    SmokeTrainingResult,
    build_episode_rollout_buffers,
    physical_team_rewards,
    run_tiny_smoke_training,
    tiny_deterministic_smoke_case,
)

__all__ += [
    "ActorLocalAIDecisionArchitecture",
    "DecisionRecord",
    "SmokeTrainingResult",
    "build_episode_rollout_buffers",
    "physical_team_rewards",
    "run_tiny_smoke_training",
    "tiny_deterministic_smoke_case",
]

from .training_runner import (
    ACTOR_NAMES,
    BoundaryAwareEpisodeRunner,
    BoundaryTrainingResult,
    RolloutUpdateEvent,
    expected_rollout_partition,
)

__all__ += [
    "ACTOR_NAMES",
    "BoundaryAwareEpisodeRunner",
    "BoundaryTrainingResult",
    "RolloutUpdateEvent",
    "expected_rollout_partition",
]

from .training_protocol import (
    AI_SPEC_BASE,
    CHECKPOINT_VERSION,
    EVALUATION_MASTER_SEED,
    FROZEN_SMOKE_BASE,
    INFORMATION_REGIMES,
    RUNNER_PROTOCOL_VERSION,
    SCENARIO_SEED_PROTOCOL_VERSION,
    TRAINING_EPISODE_DAYS,
    TRAINING_EPISODES,
    TRAINING_SEEDS,
    build_run_manifest,
    checkpoint_payload,
    episode_manifest_record,
    episode_scenario_seed,
    episode_seed_schedule,
    load_training_checkpoint,
    save_training_checkpoint,
    simulation_config_hash,
    simulation_config_payload,
    validate_finite_training_state,
    validate_run_manifest,
)

__all__ += [
    "AI_SPEC_BASE",
    "CHECKPOINT_VERSION",
    "EVALUATION_MASTER_SEED",
    "FROZEN_SMOKE_BASE",
    "INFORMATION_REGIMES",
    "RUNNER_PROTOCOL_VERSION",
    "SCENARIO_SEED_PROTOCOL_VERSION",
    "TRAINING_EPISODE_DAYS",
    "TRAINING_EPISODES",
    "TRAINING_SEEDS",
    "build_run_manifest",
    "checkpoint_payload",
    "episode_manifest_record",
    "episode_scenario_seed",
    "episode_seed_schedule",
    "load_training_checkpoint",
    "save_training_checkpoint",
    "simulation_config_hash",
    "simulation_config_payload",
    "validate_finite_training_state",
    "validate_run_manifest",
]
