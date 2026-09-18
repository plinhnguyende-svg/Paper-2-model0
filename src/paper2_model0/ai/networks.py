from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn
from torch.distributions import Normal


HIDDEN_UNITS = (64, 64)


def _mlp(input_dim: int, output_dim: int) -> nn.Sequential:
    if input_dim <= 0 or output_dim <= 0:
        raise ValueError("network dimensions must be positive")
    return nn.Sequential(
        nn.Linear(input_dim, HIDDEN_UNITS[0]),
        nn.Tanh(),
        nn.Linear(HIDDEN_UNITS[0], HIDDEN_UNITS[1]),
        nn.Tanh(),
        nn.Linear(HIDDEN_UNITS[1], output_dim),
    )


class GaussianActorCritic(nn.Module):
    """Actor-local feed-forward Gaussian policy with actor-local value network.

    The module accepts only the local encoded observation for one actor. It has
    no interface for global simulator state, regime labels, or other actors'
    observations.
    """

    def __init__(self, observation_dim: int, action_dim: int = 1):
        super().__init__()
        if observation_dim <= 0:
            raise ValueError("observation_dim must be positive")
        if action_dim <= 0:
            raise ValueError("action_dim must be positive")

        self.observation_dim = int(observation_dim)
        self.action_dim = int(action_dim)
        self.actor_mean = _mlp(self.observation_dim, self.action_dim)
        self.critic = _mlp(self.observation_dim, 1)

        # Locked implementation convention for v0.1: unit initial latent-action
        # standard deviation. This is learned thereafter.
        self.log_std = nn.Parameter(torch.zeros(self.action_dim))

    def _validate_observation(self, observation: torch.Tensor) -> torch.Tensor:
        if observation.ndim == 1:
            observation = observation.unsqueeze(0)
        if observation.ndim != 2:
            raise ValueError("observation tensor must have shape [batch, features]")
        if observation.shape[-1] != self.observation_dim:
            raise ValueError(
                f"expected observation dimension {self.observation_dim}, "
                f"got {observation.shape[-1]}"
            )
        return observation

    def distribution(self, observation: torch.Tensor) -> Normal:
        observation = self._validate_observation(observation)
        mean = self.actor_mean(observation)
        std = self.log_std.exp().expand_as(mean)
        return Normal(mean, std)

    def value(self, observation: torch.Tensor) -> torch.Tensor:
        observation = self._validate_observation(observation)
        return self.critic(observation).squeeze(-1)

    def act(
        self,
        observation: torch.Tensor,
        *,
        deterministic: bool,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        observation = self._validate_observation(observation)
        dist = self.distribution(observation)
        action = dist.mean if deterministic else dist.sample()
        log_prob = dist.log_prob(action).sum(dim=-1)
        value = self.critic(observation).squeeze(-1)
        return action, log_prob, value

    def evaluate_actions(
        self,
        observation: torch.Tensor,
        action: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        observation = self._validate_observation(observation)
        if action.ndim == 1:
            action = action.unsqueeze(-1)
        if action.ndim != 2 or action.shape[-1] != self.action_dim:
            raise ValueError(
                f"action tensor must have shape [batch, {self.action_dim}]"
            )
        if action.shape[0] != observation.shape[0]:
            raise ValueError("observation/action batch sizes do not match")

        dist = self.distribution(observation)
        log_prob = dist.log_prob(action).sum(dim=-1)
        entropy = dist.entropy().sum(dim=-1)
        value = self.critic(observation).squeeze(-1)
        return log_prob, entropy, value


@dataclass(frozen=True)
class ActorNetworkSpec:
    name: str
    observation_dim: int
    action_dim: int = 1


ACTOR_NETWORK_SPECS = (
    ActorNetworkSpec("R1", 4),
    ActorNetworkSpec("R2", 4),
    ActorNetworkSpec("R3", 4),
    ActorNetworkSpec("BQ", 6),
    ActorNetworkSpec("E1", 7),
    ActorNetworkSpec("E2", 7),
)
