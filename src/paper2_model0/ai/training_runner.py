from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd
import torch

from paper2_model0.config import SimulationConfig
from paper2_model0.domain.scenario import ExogenousScenario
from paper2_model0.engine.model import DecisionBoundary, SupplyChainModel

from .agents import ActorLocalIPPOAgent
from .environment import ActorLocalAIDecisionArchitecture, DecisionRecord
from .ppo import ActorRolloutBuffer, PPOHyperparameters, PPOUpdateStats


ACTOR_NAMES = ("R1", "R2", "R3", "BQ", "E1", "E2")


def expected_rollout_partition(
    horizon_days: int,
    rollout_length_days: int = 256,
) -> tuple[int, ...]:
    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    if rollout_length_days <= 0:
        raise ValueError("rollout_length_days must be positive")
    full, remainder = divmod(int(horizon_days), int(rollout_length_days))
    parts = [int(rollout_length_days)] * full
    if remainder:
        parts.append(int(remainder))
    return tuple(parts)


@dataclass(frozen=True)
class RolloutUpdateEvent:
    actor: str
    boundary_day: int
    transition_count: int
    terminal: bool
    bootstrap_value: float
    stats: PPOUpdateStats


@dataclass(frozen=True)
class BoundaryTrainingResult:
    regime: str
    scenario_id: str
    horizon_days: int
    rollout_partition: tuple[int, ...]
    update_events: tuple[RolloutUpdateEvent, ...]
    period_df: pd.DataFrame


class BoundaryAwareEpisodeRunner:
    """One-episode PPO runner on the frozen Model 0 daily clock.

    This is intentionally not a multi-seed/full-budget launcher. It exists to
    make rollout-boundary semantics testable before the scientific training
    jobs are authorized.
    """

    def __init__(
        self,
        *,
        config: SimulationConfig,
        regime: str,
        scenario: ExogenousScenario,
        training_seed: int,
        device: str | torch.device = "cpu",
        architecture: ActorLocalAIDecisionArchitecture | None = None,
    ):
        config.validate()
        if scenario.consumer_demand.shape[0] != config.simulation_horizon_days:
            raise ValueError("scenario horizon does not match config")

        self.config = config
        self.regime = regime
        self.scenario = scenario
        self.training_seed = int(training_seed)
        self.device = torch.device(device)
        self.hyperparameters = PPOHyperparameters()
        self.hyperparameters.validate_locked_v01()

        if architecture is None:
            self.architecture = ActorLocalAIDecisionArchitecture(
                config,
                training_seed=self.training_seed,
                deterministic=False,
                device=self.device,
                before_actor_decision=self._before_actor_decision,
            )
        else:
            if architecture.config != config:
                raise ValueError("reused AI architecture config does not match runner config")
            if int(architecture.training_seed) != self.training_seed:
                raise ValueError(
                    "reused AI architecture training seed does not match runner seed"
                )
            self.architecture = architecture
            self.architecture.set_before_actor_decision_hook(
                self._before_actor_decision
            )

        # Episode boundaries reset physical Model 0 state and diagnostic traces,
        # but learned actor/critic, optimizer, and RNG states continue.
        self.architecture.clear_episode_records()

        self.model = SupplyChainModel(
            config,
            regime,
            scenario,
            decision_architecture=self.architecture,
        )
        self.buffers = {
            name: ActorRolloutBuffer(
                observation_dim=self.architecture.agents[name].network.observation_dim,
                action_dim=self.architecture.agents[name].network.action_dim,
            )
            for name in ACTOR_NAMES
        }
        self.update_events: list[RolloutUpdateEvent] = []
        self._current_boundary_day: int | None = None
        self._last_completed_row: dict | None = None
        self._finalized_days: set[int] = set()

    @property
    def aggregate_mean_demand(self) -> float:
        value = float(sum(self.config.retailer_mean_demand))
        if value <= 0.0:
            raise ValueError("aggregate mean demand must be positive for AI reward")
        return value

    def _record_for_day(self, actor: str, day: int) -> DecisionRecord:
        records = self.architecture.records_by_actor()[actor]
        if not records:
            raise AssertionError(f"{actor} has no decision record for day {day}")
        record = records[-1]
        if record.day != day:
            raise AssertionError(
                f"{actor} latest decision day {record.day} does not match {day}"
            )
        return record

    def _append_finalized_transition(
        self,
        *,
        day: int,
        reward: float,
        done: bool,
    ) -> None:
        if day in self._finalized_days:
            raise AssertionError(f"transition day {day} finalized twice")
        if not math.isfinite(float(reward)):
            raise FloatingPointError("non-finite transition reward")

        for actor in ACTOR_NAMES:
            record = self._record_for_day(actor, day)
            self.buffers[actor].add(
                observation=record.observation,
                action=record.latent_action,
                log_prob=record.log_prob,
                reward=float(reward),
                value=record.value,
                done=bool(done),
                policy_active=record.policy_active,
            )
        self._finalized_days.add(day)

    def _finalize_previous_at_boundary(
        self,
        boundary: DecisionBoundary,
    ) -> None:
        if boundary.day == 0:
            return
        row = self._last_completed_row
        if row is None or int(row["day"]) != boundary.day - 1:
            raise AssertionError("previous completed day is not aligned with boundary")

        reward = -(
            float(row["on_hand_waste"])
            + float(boundary.transit_waste)
            + float(sum(boundary.lost))
        ) / self.aggregate_mean_demand
        self._append_finalized_transition(
            day=boundary.day - 1,
            reward=reward,
            done=False,
        )

    def _before_actor_decision(
        self,
        actor_name: str,
        encoded_observation: np.ndarray,
        agent: ActorLocalIPPOAgent,
    ) -> None:
        buffer = self.buffers[actor_name]
        target = self.hyperparameters.rollout_length_days
        if len(buffer) > target:
            raise AssertionError("rollout buffer exceeded locked length")
        if len(buffer) < target:
            return
        if self._current_boundary_day is None:
            raise AssertionError("nonterminal PPO update lacks an open boundary")

        bootstrap_value = agent.value(encoded_observation)
        if not math.isfinite(bootstrap_value):
            raise FloatingPointError("non-finite bootstrap value")

        batch = buffer.training_batch(
            last_value=bootstrap_value,
            hyperparameters=self.hyperparameters,
            device=agent.device,
        )
        stats = agent.updater.update(batch)
        self.update_events.append(
            RolloutUpdateEvent(
                actor=actor_name,
                boundary_day=self._current_boundary_day,
                transition_count=len(buffer),
                terminal=False,
                bootstrap_value=float(bootstrap_value),
                stats=stats,
            )
        )
        buffer.clear()

    def _finalize_terminal_transition(self, row: dict) -> None:
        day = int(row["day"])
        reward = -(
            float(row["on_hand_waste"])
            + float(row["total_on_hand_inventory"])
            + float(row["total_pipeline_inventory"])
        ) / self.aggregate_mean_demand
        self._append_finalized_transition(
            day=day,
            reward=reward,
            done=True,
        )

    def _flush_terminal_updates(self, terminal_boundary_day: int) -> None:
        for actor in ACTOR_NAMES:
            buffer = self.buffers[actor]
            if len(buffer) == 0:
                continue
            agent = self.architecture.agents[actor]
            batch = buffer.training_batch(
                last_value=0.0,
                hyperparameters=self.hyperparameters,
                device=agent.device,
            )
            stats = agent.updater.update(batch)
            self.update_events.append(
                RolloutUpdateEvent(
                    actor=actor,
                    boundary_day=int(terminal_boundary_day),
                    transition_count=len(buffer),
                    terminal=True,
                    bootstrap_value=0.0,
                    stats=stats,
                )
            )
            buffer.clear()

    def run_episode(self) -> BoundaryTrainingResult:
        horizon = self.config.simulation_horizon_days
        for day in range(horizon):
            boundary = self.model.open_decision_boundary(day)
            self._current_boundary_day = day
            self._finalize_previous_at_boundary(boundary)

            # complete_decision_boundary invokes the actor-local pre-action
            # hook. At a 256-transition boundary the previous chunk is updated
            # and cleared before that actor samples its current action.
            row = self.model.complete_decision_boundary(boundary)
            self._last_completed_row = row
            self._current_boundary_day = None

        if self._last_completed_row is None:
            raise AssertionError("episode produced no completed day")

        self._finalize_terminal_transition(self._last_completed_row)
        self._flush_terminal_updates(horizon)

        if len(self._finalized_days) != horizon:
            raise AssertionError("not every episode transition was finalized")
        if any(len(buffer) for buffer in self.buffers.values()):
            raise AssertionError("terminal PPO flush left non-empty buffers")

        partition = expected_rollout_partition(
            horizon,
            self.hyperparameters.rollout_length_days,
        )
        for actor in ACTOR_NAMES:
            observed = tuple(
                event.transition_count
                for event in self.update_events
                if event.actor == actor
            )
            if observed != partition:
                raise AssertionError(
                    f"{actor} rollout partition {observed} != expected {partition}"
                )

        return BoundaryTrainingResult(
            regime=self.regime,
            scenario_id=self.scenario.scenario_id,
            horizon_days=horizon,
            rollout_partition=partition,
            update_events=tuple(self.update_events),
            period_df=self.model.recorder.dataframe(),
        )
