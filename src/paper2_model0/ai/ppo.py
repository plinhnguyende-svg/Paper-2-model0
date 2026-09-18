from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import torch
from torch import nn

from .networks import GaussianActorCritic


@dataclass(frozen=True)
class PPOHyperparameters:
    learning_rate: float = 3e-4
    gamma: float = 1.0
    gae_lambda: float = 0.95
    clip_range: float = 0.20
    value_loss_coefficient: float = 0.50
    entropy_coefficient: float = 0.01
    max_gradient_norm: float = 0.50
    rollout_length_days: int = 256
    minibatch_size: int = 64
    update_epochs: int = 10

    def validate_locked_v01(self) -> None:
        expected = PPOHyperparameters()
        if self != expected:
            raise ValueError(
                "AI v0.1 PPO hyperparameters are locked by the merged "
                "scientific specification."
            )


@dataclass(frozen=True)
class PPOTrainingBatch:
    observations: torch.Tensor
    actions: torch.Tensor
    old_log_probs: torch.Tensor
    returns: torch.Tensor
    advantages: torch.Tensor
    policy_mask: torch.Tensor | None = None

    def validate(self, observation_dim: int, action_dim: int) -> int:
        tensors = (
            self.observations,
            self.actions,
            self.old_log_probs,
            self.returns,
            self.advantages,
        )
        if any(not torch.isfinite(t).all() for t in tensors):
            raise ValueError("PPO batch contains non-finite values")
        n = int(self.observations.shape[0])
        if n == 0:
            raise ValueError("PPO batch must be non-empty")
        if self.observations.ndim != 2 or self.observations.shape[1] != observation_dim:
            raise ValueError("invalid observation batch shape")
        if self.actions.ndim != 2 or self.actions.shape != (n, action_dim):
            raise ValueError("invalid action batch shape")
        for tensor in (self.old_log_probs, self.returns, self.advantages):
            if tensor.ndim != 1 or tensor.shape[0] != n:
                raise ValueError("invalid scalar-vector batch shape")
        if self.policy_mask is not None:
            if self.policy_mask.ndim != 1 or self.policy_mask.shape[0] != n:
                raise ValueError("invalid policy-mask batch shape")
        return n


@dataclass(frozen=True)
class PPOUpdateStats:
    policy_loss: float
    value_loss: float
    entropy: float
    total_loss: float
    approximate_kl: float
    clip_fraction: float
    gradient_norm: float
    minibatch_updates: int


class ActorRolloutBuffer:
    """Actor-local rollout storage.

    The buffer stores only one actor's encoded local observation and PPO
    quantities. It has no fields for raw simulator state, regime labels, or
    other actors' observations.
    """

    def __init__(self, observation_dim: int, action_dim: int = 1):
        if observation_dim <= 0 or action_dim <= 0:
            raise ValueError("buffer dimensions must be positive")
        self.observation_dim = int(observation_dim)
        self.action_dim = int(action_dim)
        self.clear()

    def clear(self) -> None:
        self.observations: list[np.ndarray] = []
        self.actions: list[np.ndarray] = []
        self.log_probs: list[float] = []
        self.rewards: list[float] = []
        self.values: list[float] = []
        self.dones: list[bool] = []
        self.policy_masks: list[bool] = []

    def __len__(self) -> int:
        return len(self.rewards)

    def add(
        self,
        observation: np.ndarray,
        action: np.ndarray,
        log_prob: float,
        reward: float,
        value: float,
        done: bool,
        policy_active: bool = True,
    ) -> None:
        observation = np.asarray(observation, dtype=np.float32)
        action = np.asarray(action, dtype=np.float32)
        if observation.shape != (self.observation_dim,):
            raise ValueError("rollout observation has wrong shape")
        if action.shape != (self.action_dim,):
            raise ValueError("rollout action has wrong shape")
        scalars = (log_prob, reward, value)
        if not all(math.isfinite(float(x)) for x in scalars):
            raise ValueError("rollout contains non-finite scalar")
        if not np.isfinite(observation).all() or not np.isfinite(action).all():
            raise ValueError("rollout contains non-finite vector")

        self.observations.append(observation.copy())
        self.actions.append(action.copy())
        self.log_probs.append(float(log_prob))
        self.rewards.append(float(reward))
        self.values.append(float(value))
        self.dones.append(bool(done))
        self.policy_masks.append(bool(policy_active))

    def training_batch(
        self,
        *,
        last_value: float,
        hyperparameters: PPOHyperparameters,
        device: torch.device | str = "cpu",
    ) -> PPOTrainingBatch:
        hyperparameters.validate_locked_v01()
        if len(self) == 0:
            raise ValueError("cannot build PPO batch from an empty rollout")
        advantages, returns = compute_gae(
            rewards=np.asarray(self.rewards, dtype=np.float64),
            values=np.asarray(self.values, dtype=np.float64),
            dones=np.asarray(self.dones, dtype=np.bool_),
            last_value=float(last_value),
            gamma=hyperparameters.gamma,
            gae_lambda=hyperparameters.gae_lambda,
        )
        return PPOTrainingBatch(
            observations=torch.as_tensor(
                np.stack(self.observations), dtype=torch.float32, device=device
            ),
            actions=torch.as_tensor(
                np.stack(self.actions), dtype=torch.float32, device=device
            ),
            old_log_probs=torch.as_tensor(
                self.log_probs, dtype=torch.float32, device=device
            ),
            returns=torch.as_tensor(
                returns, dtype=torch.float32, device=device
            ),
            advantages=torch.as_tensor(
                advantages, dtype=torch.float32, device=device
            ),
            policy_mask=torch.as_tensor(
                self.policy_masks, dtype=torch.bool, device=device
            ),
        )


def compute_gae(
    *,
    rewards: np.ndarray,
    values: np.ndarray,
    dones: np.ndarray,
    last_value: float,
    gamma: float,
    gae_lambda: float,
) -> tuple[np.ndarray, np.ndarray]:
    rewards = np.asarray(rewards, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    dones = np.asarray(dones, dtype=np.bool_)

    if rewards.ndim != 1 or values.ndim != 1 or dones.ndim != 1:
        raise ValueError("GAE inputs must be one-dimensional")
    if not (len(rewards) == len(values) == len(dones)):
        raise ValueError("GAE input lengths must match")
    if len(rewards) == 0:
        raise ValueError("GAE inputs must be non-empty")
    if not np.isfinite(rewards).all() or not np.isfinite(values).all():
        raise ValueError("GAE inputs must be finite")
    if not math.isfinite(float(last_value)):
        raise ValueError("last_value must be finite")

    advantages = np.zeros_like(rewards, dtype=np.float64)
    gae = 0.0
    for t in range(len(rewards) - 1, -1, -1):
        next_value = float(last_value) if t == len(rewards) - 1 else float(values[t + 1])
        nonterminal = 0.0 if dones[t] else 1.0
        delta = rewards[t] + gamma * next_value * nonterminal - values[t]
        gae = delta + gamma * gae_lambda * nonterminal * gae
        advantages[t] = gae

    returns = advantages + values
    return advantages, returns


class PPOUpdater:
    """One actor-local PPO optimizer.

    There is one updater per actor policy. No model or optimizer is shared
    across retailers, importer, or exporters.
    """

    def __init__(
        self,
        model: GaussianActorCritic,
        *,
        hyperparameters: PPOHyperparameters | None = None,
        shuffle_seed: int,
    ):
        self.model = model
        self.hyperparameters = hyperparameters or PPOHyperparameters()
        self.hyperparameters.validate_locked_v01()
        self.optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.hyperparameters.learning_rate,
        )
        self._shuffle_generator = torch.Generator(device="cpu")
        self._shuffle_generator.manual_seed(int(shuffle_seed))

    def checkpoint_state(self) -> dict:
        """Crash-recovery state required for deterministic PPO continuation."""
        return {
            "optimizer": self.optimizer.state_dict(),
            "shuffle_generator_state": self._shuffle_generator.get_state().clone(),
        }

    def load_checkpoint_state(self, state: dict) -> None:
        if set(state) != {"optimizer", "shuffle_generator_state"}:
            raise ValueError("invalid PPO updater checkpoint state")
        self.optimizer.load_state_dict(state["optimizer"])
        generator_state = state["shuffle_generator_state"]
        if not isinstance(generator_state, torch.Tensor):
            raise ValueError("shuffle generator state must be a tensor")
        self._shuffle_generator.set_state(generator_state.cpu())

    def update(self, batch: PPOTrainingBatch) -> PPOUpdateStats:
        hp = self.hyperparameters
        n = batch.validate(
            self.model.observation_dim,
            self.model.action_dim,
        )

        policy_losses: list[float] = []
        value_losses: list[float] = []
        entropies: list[float] = []
        total_losses: list[float] = []
        approximate_kls: list[float] = []
        clip_fractions: list[float] = []
        gradient_norms: list[float] = []
        update_count = 0

        for _ in range(hp.update_epochs):
            permutation = torch.randperm(
                n,
                generator=self._shuffle_generator,
                device="cpu",
            )
            for start in range(0, n, hp.minibatch_size):
                index = permutation[start : start + hp.minibatch_size].to(
                    batch.observations.device
                )
                obs = batch.observations[index]
                actions = batch.actions[index]
                old_log_prob = batch.old_log_probs[index]
                returns = batch.returns[index]
                advantages = batch.advantages[index]
                policy_mask = (
                    torch.ones_like(advantages, dtype=torch.bool)
                    if batch.policy_mask is None
                    else batch.policy_mask[index].bool()
                )

                new_log_prob, entropy, values = self.model.evaluate_actions(
                    obs, actions
                )
                log_ratio = new_log_prob - old_log_prob
                ratio = log_ratio.exp()
                value_loss = torch.mean((values - returns) ** 2)

                if torch.any(policy_mask):
                    active_ratio = ratio[policy_mask]
                    active_advantages = advantages[policy_mask]
                    active_log_ratio = log_ratio[policy_mask]
                    unclipped = active_ratio * active_advantages
                    clipped = torch.clamp(
                        active_ratio,
                        1.0 - hp.clip_range,
                        1.0 + hp.clip_range,
                    ) * active_advantages
                    policy_loss = -torch.min(unclipped, clipped).mean()
                    entropy_mean = entropy[policy_mask].mean()
                else:
                    policy_loss = values.sum() * 0.0
                    entropy_mean = values.sum() * 0.0
                total_loss = (
                    policy_loss
                    + hp.value_loss_coefficient * value_loss
                    - hp.entropy_coefficient * entropy_mean
                )

                if not torch.isfinite(total_loss):
                    raise FloatingPointError("non-finite PPO loss")

                self.optimizer.zero_grad(set_to_none=True)
                total_loss.backward()
                grad_norm = nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    hp.max_gradient_norm,
                )
                if not torch.isfinite(torch.as_tensor(grad_norm)):
                    raise FloatingPointError("non-finite PPO gradient norm")
                self.optimizer.step()

                with torch.no_grad():
                    if torch.any(policy_mask):
                        active_ratio = ratio[policy_mask]
                        active_log_ratio = log_ratio[policy_mask]
                        approximate_kl = (
                            (active_ratio - 1.0) - active_log_ratio
                        ).mean()
                        clip_fraction = (
                            (torch.abs(active_ratio - 1.0) > hp.clip_range)
                            .float()
                            .mean()
                        )
                    else:
                        approximate_kl = torch.zeros(
                            (), device=values.device
                        )
                        clip_fraction = torch.zeros(
                            (), device=values.device
                        )

                policy_losses.append(float(policy_loss.detach().cpu()))
                value_losses.append(float(value_loss.detach().cpu()))
                entropies.append(float(entropy_mean.detach().cpu()))
                total_losses.append(float(total_loss.detach().cpu()))
                approximate_kls.append(float(approximate_kl.detach().cpu()))
                clip_fractions.append(float(clip_fraction.detach().cpu()))
                gradient_norms.append(float(torch.as_tensor(grad_norm).detach().cpu()))
                update_count += 1

        return PPOUpdateStats(
            policy_loss=float(np.mean(policy_losses)),
            value_loss=float(np.mean(value_losses)),
            entropy=float(np.mean(entropies)),
            total_loss=float(np.mean(total_losses)),
            approximate_kl=float(np.mean(approximate_kls)),
            clip_fraction=float(np.mean(clip_fractions)),
            gradient_norm=float(np.mean(gradient_norms)),
            minibatch_updates=update_count,
        )
