from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd
import torch

from paper2_model0.config import SimulationConfig
from paper2_model0.decision_architectures import validate_decision_architecture
from paper2_model0.domain.observations import (
    ExporterObservation,
    ImporterObservation,
    ImporterReplenishmentObservation,
    RetailerObservation,
)
from paper2_model0.domain.scenario import ExogenousScenario, deterministic_scenario
from paper2_model0.engine.model import SupplyChainModel
from paper2_model0.policies.importer_allocation import RuleBasedImporterAllocationPolicy

from .agents import ActorLocalIPPOAgent, build_actor_local_ippo_agents
from .encoders import AIObservationEncoder
from .forecast import FixedForecastTransitionAdapter
from .ppo import ActorRolloutBuffer, PPOHyperparameters, PPOUpdateStats
from .transforms import BoundedActionTransformer


BeforeActorDecisionHook = Callable[
    [str, np.ndarray, ActorLocalIPPOAgent],
    None,
]


@dataclass(frozen=True)
class DecisionRecord:
    day: int
    observation: np.ndarray
    latent_action: np.ndarray
    log_prob: float
    value: float
    policy_active: bool


class _AIRetailerPolicy:
    def __init__(
        self,
        *,
        retailer_index: int,
        agent: ActorLocalIPPOAgent,
        encoder: AIObservationEncoder,
        transformer: BoundedActionTransformer,
        deterministic: bool,
        before_decision: BeforeActorDecisionHook | None = None,
    ):
        self.retailer_index = int(retailer_index)
        self.actor_name = f"R{self.retailer_index + 1}"
        self.agent = agent
        self.encoder = encoder
        self.transformer = transformer
        self.deterministic = bool(deterministic)
        self.before_decision = before_decision
        self.records: list[DecisionRecord] = []

    def decide(self, observation: RetailerObservation):
        encoded = self.encoder.encode_retailer(
            observation,
            self.retailer_index,
        )
        if self.before_decision is not None:
            self.before_decision(self.actor_name, encoded, self.agent)
        latent, log_prob, value = self.agent.act(
            encoded,
            deterministic=self.deterministic,
        )
        self.records.append(
            DecisionRecord(
                day=int(observation.current_day),
                observation=encoded.copy(),
                latent_action=latent.copy(),
                log_prob=float(log_prob),
                value=float(value),
                policy_active=True,
            )
        )
        return self.transformer.retailer_action(
            float(latent[0]),
            observation,
            self.retailer_index,
        )


class _AIImporterPolicy:
    def __init__(
        self,
        *,
        agent: ActorLocalIPPOAgent,
        encoder: AIObservationEncoder,
        transformer: BoundedActionTransformer,
        deterministic: bool,
        before_decision: BeforeActorDecisionHook | None = None,
    ):
        self.actor_name = "BQ"
        self.agent = agent
        self.encoder = encoder
        self.transformer = transformer
        self.deterministic = bool(deterministic)
        self.before_decision = before_decision
        self.allocation_policy = RuleBasedImporterAllocationPolicy()
        self.records: list[DecisionRecord] = []

    def decide_replenishment(
        self,
        observation: ImporterReplenishmentObservation,
    ):
        encoded = self.encoder.encode_importer_replenishment(observation)
        if self.before_decision is not None:
            self.before_decision(self.actor_name, encoded, self.agent)
        latent, log_prob, value = self.agent.act(
            encoded,
            deterministic=self.deterministic,
        )
        self.records.append(
            DecisionRecord(
                day=int(observation.current_day),
                observation=encoded.copy(),
                latent_action=latent.copy(),
                log_prob=float(log_prob),
                value=float(value),
                policy_active=True,
            )
        )
        return self.transformer.importer_replenishment_action(
            float(latent[0]),
            observation,
        )

    def decide_allocation(
        self,
        procurement_requirement: float,
        observation: ImporterObservation,
    ) -> tuple[float, float]:
        # Frozen N/S/F institution: allocation is never an AI action in v0.1.
        return self.allocation_policy.decide(
            procurement_requirement,
            observation,
        )


class _AIExporterPolicy:
    def __init__(
        self,
        *,
        agent: ActorLocalIPPOAgent,
        encoder: AIObservationEncoder,
        transformer: BoundedActionTransformer,
        deterministic: bool,
        actor_name: str,
        before_decision: BeforeActorDecisionHook | None = None,
    ):
        self.actor_name = str(actor_name)
        self.agent = agent
        self.encoder = encoder
        self.transformer = transformer
        self.deterministic = bool(deterministic)
        self.before_decision = before_decision
        self.records: list[DecisionRecord] = []

    def decide(self, observation: ExporterObservation):
        encoded = self.encoder.encode_exporter(observation)
        if self.before_decision is not None:
            self.before_decision(self.actor_name, encoded, self.agent)

        if observation.own_operational_availability:
            latent, log_prob, value = self.agent.act(
                encoded,
                deterministic=self.deterministic,
            )
            policy_active = True
        else:
            # Unavailable exporters have no decision right in v0.1. Keep the
            # day in the critic/reward timeline, but do not sample an action or
            # create a policy-gradient contribution.
            latent = np.zeros(
                self.agent.network.action_dim,
                dtype=np.float32,
            )
            tensor = torch.as_tensor(
                encoded,
                dtype=torch.float32,
                device=self.agent.device,
            )
            with torch.no_grad():
                value = float(
                    self.agent.network.value(tensor).squeeze(0).cpu()
                )
            log_prob = 0.0
            policy_active = False

        self.records.append(
            DecisionRecord(
                day=int(observation.current_day),
                observation=encoded.copy(),
                latent_action=latent.copy(),
                log_prob=float(log_prob),
                value=float(value),
                policy_active=policy_active,
            )
        )
        return self.transformer.exporter_readiness_action(
            float(latent[0]),
            observation,
        )


class ActorLocalAIDecisionArchitecture:
    """Actor-isolated AI decision adapter for environment integration.

    The container receives no observations. Engine calls are routed directly
    to six distinct policy objects. Importer allocation remains deterministic.
    """

    name = "AI-IPPO-v0.1"

    def __init__(
        self,
        config: SimulationConfig,
        *,
        training_seed: int,
        deterministic: bool = False,
        device: str | torch.device = "cpu",
        before_actor_decision: BeforeActorDecisionHook | None = None,
    ):
        self.config = config
        self.training_seed = int(training_seed)
        self.before_actor_decision = before_actor_decision
        self.encoder = AIObservationEncoder.from_config(config)
        self.transformer = BoundedActionTransformer(
            shelf_life_days=config.shelf_life_days,
            retailer_mean_demand=tuple(
                float(x) for x in config.retailer_mean_demand
            ),  # type: ignore[arg-type]
            forecast_transition=FixedForecastTransitionAdapter(
                config.demand_forecast_smoothing_weight
            ),
        )
        self.agents = build_actor_local_ippo_agents(
            training_seed=training_seed,
            device=device,
        )
        self.retailer_policies = (
            _AIRetailerPolicy(
                retailer_index=0,
                agent=self.agents["R1"],
                encoder=self.encoder,
                transformer=self.transformer,
                deterministic=deterministic,
                before_decision=self.before_actor_decision,
            ),
            _AIRetailerPolicy(
                retailer_index=1,
                agent=self.agents["R2"],
                encoder=self.encoder,
                transformer=self.transformer,
                deterministic=deterministic,
                before_decision=self.before_actor_decision,
            ),
            _AIRetailerPolicy(
                retailer_index=2,
                agent=self.agents["R3"],
                encoder=self.encoder,
                transformer=self.transformer,
                deterministic=deterministic,
                before_decision=self.before_actor_decision,
            ),
        )
        self.importer_policy = _AIImporterPolicy(
            agent=self.agents["BQ"],
            encoder=self.encoder,
            transformer=self.transformer,
            deterministic=deterministic,
            before_decision=self.before_actor_decision,
        )
        self.exporter_policies = (
            _AIExporterPolicy(
                agent=self.agents["E1"],
                encoder=self.encoder,
                transformer=self.transformer,
                deterministic=deterministic,
                actor_name="E1",
                before_decision=self.before_actor_decision,
            ),
            _AIExporterPolicy(
                agent=self.agents["E2"],
                encoder=self.encoder,
                transformer=self.transformer,
                deterministic=deterministic,
                actor_name="E2",
                before_decision=self.before_actor_decision,
            ),
        )
        validate_decision_architecture(self)

    def set_before_actor_decision_hook(
        self,
        hook: BeforeActorDecisionHook | None,
    ) -> None:
        self.before_actor_decision = hook
        for policy in self.retailer_policies:
            policy.before_decision = hook
        self.importer_policy.before_decision = hook
        for policy in self.exporter_policies:
            policy.before_decision = hook

    def clear_episode_records(self) -> None:
        """Clear diagnostic decision traces without touching learned state.

        Networks, optimizer state, action RNGs, and PPO shuffle RNGs persist
        across episodes. Only per-episode trace records are reset so a
        1000-episode run does not accumulate millions of stale DecisionRecord
        objects or blur episode boundaries.
        """
        for records in self.records_by_actor().values():
            records.clear()

    def records_by_actor(self) -> dict[str, list[DecisionRecord]]:
        return {
            "R1": self.retailer_policies[0].records,
            "R2": self.retailer_policies[1].records,
            "R3": self.retailer_policies[2].records,
            "BQ": self.importer_policy.records,
            "E1": self.exporter_policies[0].records,
            "E2": self.exporter_policies[1].records,
        }


def physical_team_rewards(
    period_df: pd.DataFrame,
    *,
    aggregate_mean_demand: float,
) -> np.ndarray:
    if aggregate_mean_demand <= 0.0:
        raise ValueError("aggregate_mean_demand must be positive")
    required = {
        "aggregate_lost_sales",
        "on_hand_waste",
        "transit_waste",
        "total_on_hand_inventory",
        "total_pipeline_inventory",
    }
    missing = required.difference(period_df.columns)
    if missing:
        raise ValueError(f"period_df missing reward columns: {sorted(missing)}")
    if len(period_df) == 0:
        raise ValueError("period_df must be non-empty")

    lost_sales = period_df["aggregate_lost_sales"].to_numpy(dtype=float)
    on_hand_waste = period_df["on_hand_waste"].to_numpy(dtype=float)
    transit_waste = period_df["transit_waste"].to_numpy(dtype=float)

    # Timing in Model 0:
    #   start of day: receive shipments -> transit waste; serve demand -> lost sales
    #   then choose replenishment/readiness actions
    #   end of day: age on-hand inventory -> on-hand waste.
    # Therefore current-day transit waste and lost sales are pre-action. Attach
    # next-day pre-action consequences to the current decision transition,
    # while current-day on-hand waste is post-action.
    rewards = -on_hand_waste / float(aggregate_mean_demand)
    if len(rewards) > 1:
        rewards[:-1] -= (
            lost_sales[1:] + transit_waste[1:]
        ) / float(aggregate_mean_demand)

    rewards = np.asarray(rewards, dtype=np.float64)
    rewards[-1] -= float(
        period_df.iloc[-1]["total_on_hand_inventory"]
        + period_df.iloc[-1]["total_pipeline_inventory"]
    ) / float(aggregate_mean_demand)

    if not np.isfinite(rewards).all():
        raise ValueError("physical team reward contains non-finite values")
    return rewards


def build_episode_rollout_buffers(
    *,
    architecture: ActorLocalAIDecisionArchitecture,
    period_df: pd.DataFrame,
) -> tuple[dict[str, ActorRolloutBuffer], np.ndarray]:
    rewards = physical_team_rewards(
        period_df,
        aggregate_mean_demand=architecture.encoder.aggregate_mean_demand,
    )
    expected_days = period_df["day"].to_numpy(dtype=int)
    records = architecture.records_by_actor()

    buffers: dict[str, ActorRolloutBuffer] = {}
    for actor_name, actor_records in records.items():
        if len(actor_records) != len(period_df):
            raise AssertionError(
                f"{actor_name} produced {len(actor_records)} decisions for "
                f"{len(period_df)} environment days"
            )
        record_days = np.asarray([record.day for record in actor_records], dtype=int)
        if not np.array_equal(record_days, expected_days):
            raise AssertionError(
                f"{actor_name} decision days do not align with environment rows"
            )

        agent = architecture.agents[actor_name]
        buffer = ActorRolloutBuffer(
            observation_dim=agent.network.observation_dim,
            action_dim=agent.network.action_dim,
        )
        for index, record in enumerate(actor_records):
            buffer.add(
                observation=record.observation,
                action=record.latent_action,
                log_prob=record.log_prob,
                reward=float(rewards[index]),
                value=record.value,
                done=(index == len(actor_records) - 1),
                policy_active=record.policy_active,
            )
        buffers[actor_name] = buffer

    return buffers, rewards


@dataclass(frozen=True)
class SmokeTrainingResult:
    regime: str
    scenario_id: str
    horizon_days: int
    total_team_reward: float
    actor_buffer_lengths: dict[str, int]
    parameter_changed: dict[str, bool]
    update_stats: dict[str, PPOUpdateStats]

    def to_dict(self) -> dict:
        return {
            "regime": self.regime,
            "scenario_id": self.scenario_id,
            "horizon_days": self.horizon_days,
            "total_team_reward": self.total_team_reward,
            "actor_buffer_lengths": dict(self.actor_buffer_lengths),
            "parameter_changed": dict(self.parameter_changed),
            "update_stats": {
                actor: asdict(stats)
                for actor, stats in self.update_stats.items()
            },
        }


def run_tiny_smoke_training(
    *,
    regime: str,
    config: SimulationConfig,
    scenario: ExogenousScenario,
    training_seed: int = 41001,
    device: str | torch.device = "cpu",
) -> SmokeTrainingResult:
    if config.simulation_horizon_days != len(scenario.consumer_demand):
        raise ValueError("smoke scenario horizon must match config")

    architecture = ActorLocalAIDecisionArchitecture(
        config,
        training_seed=training_seed,
        deterministic=False,
        device=device,
    )
    before = {
        name: [
            parameter.detach().cpu().clone()
            for parameter in agent.network.parameters()
        ]
        for name, agent in architecture.agents.items()
    }

    period_df = SupplyChainModel(
        config,
        regime,
        scenario,
        decision_architecture=architecture,
    ).run()

    buffers, rewards = build_episode_rollout_buffers(
        architecture=architecture,
        period_df=period_df,
    )
    hp = PPOHyperparameters()
    update_stats: dict[str, PPOUpdateStats] = {}
    for actor_name, buffer in buffers.items():
        agent = architecture.agents[actor_name]
        batch = buffer.training_batch(
            last_value=0.0,
            hyperparameters=hp,
            device=agent.device,
        )
        update_stats[actor_name] = agent.updater.update(batch)

    changed = {}
    for actor_name, agent in architecture.agents.items():
        after = [
            parameter.detach().cpu()
            for parameter in agent.network.parameters()
        ]
        changed[actor_name] = any(
            not torch.equal(pre, post)
            for pre, post in zip(before[actor_name], after)
        )

    return SmokeTrainingResult(
        regime=regime,
        scenario_id=scenario.scenario_id,
        horizon_days=len(period_df),
        total_team_reward=float(rewards.sum()),
        actor_buffer_lengths={
            name: len(buffer)
            for name, buffer in buffers.items()
        },
        parameter_changed=changed,
        update_stats=update_stats,
    )


def tiny_deterministic_smoke_case() -> tuple[SimulationConfig, ExogenousScenario]:
    config = SimulationConfig(
        simulation_horizon_days=8,
        warmup_days=0,
        shelf_life_days=3,
        exporter_to_importer_lead_time_days=1,
        importer_to_retailer_lead_time_days=1,
        retailer_mean_demand=(10.0, 10.0, 10.0),
        demand_forecast_smoothing_weight=0.30,
        exporter_availability_probability=(0.75, 0.75),
    )
    demand = np.asarray(
        [
            [10, 10, 10],
            [12, 9, 11],
            [8, 13, 10],
            [11, 10, 12],
            [14, 8, 9],
            [9, 12, 13],
            [10, 11, 8],
            [13, 10, 12],
        ],
        dtype=float,
    )
    availability = np.asarray(
        [
            [1, 1],
            [1, 0],
            [0, 1],
            [1, 1],
            [0, 0],
            [1, 0],
            [0, 1],
            [1, 1],
        ],
        dtype=bool,
    )
    return config, deterministic_scenario(
        demand,
        availability,
        seed=909001,
    )
