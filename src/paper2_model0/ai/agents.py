from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from .networks import ACTOR_NETWORK_SPECS, ActorNetworkSpec, GaussianActorCritic
from .ppo import PPOHyperparameters, PPOUpdater


@dataclass
class ActorLocalIPPOAgent:
    name: str
    network: GaussianActorCritic
    updater: PPOUpdater
    device: torch.device
    action_generator: torch.Generator

    def act(
        self,
        observation: np.ndarray,
        *,
        deterministic: bool,
    ) -> tuple[np.ndarray, float, float]:
        observation = np.asarray(observation, dtype=np.float32)
        if observation.shape != (self.network.observation_dim,):
            raise ValueError(
                f"{self.name} expected observation shape "
                f"({self.network.observation_dim},)"
            )
        tensor = torch.as_tensor(
            observation,
            dtype=torch.float32,
            device=self.device,
        )
        with torch.no_grad():
            dist = self.network.distribution(tensor)
            if deterministic:
                action = dist.mean
            else:
                # Use an actor-local CPU generator so stochastic action streams
                # are reproducible and independent of global torch RNG state.
                noise = torch.randn(
                    dist.mean.shape,
                    generator=self.action_generator,
                    dtype=dist.mean.dtype,
                    device="cpu",
                ).to(self.device)
                action = dist.mean + dist.stddev * noise
            log_prob = dist.log_prob(action).sum(dim=-1)
            value = self.network.value(tensor)
        return (
            action.squeeze(0).cpu().numpy().copy(),
            float(log_prob.squeeze(0).cpu()),
            float(value.squeeze(0).cpu()),
        )


def _build_seed(training_seed: int, actor_index: int) -> int:
    return int(training_seed) * 100 + int(actor_index)


def build_actor_local_ippo_agents(
    *,
    training_seed: int,
    device: str | torch.device = "cpu",
) -> dict[str, ActorLocalIPPOAgent]:
    """Build the six distinct learnable actor agents for AI v0.1.

    The same training seed produces the same actor-specific initialization
    convention in N, S, and F because this factory has no regime argument.
    """

    device = torch.device(device)
    hp = PPOHyperparameters()
    hp.validate_locked_v01()
    agents: dict[str, ActorLocalIPPOAgent] = {}

    for actor_index, spec in enumerate(ACTOR_NETWORK_SPECS):
        actor_seed = _build_seed(training_seed, actor_index)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(actor_seed)
            network = GaussianActorCritic(
                observation_dim=spec.observation_dim,
                action_dim=spec.action_dim,
            ).to(device)

        updater = PPOUpdater(
            network,
            hyperparameters=hp,
            shuffle_seed=actor_seed + 50_000,
        )
        action_generator = torch.Generator(device="cpu")
        action_generator.manual_seed(actor_seed + 25_000)
        agents[spec.name] = ActorLocalIPPOAgent(
            name=spec.name,
            network=network,
            updater=updater,
            device=device,
            action_generator=action_generator,
        )

    _validate_no_parameter_sharing(agents)
    return agents


def _validate_no_parameter_sharing(
    agents: dict[str, ActorLocalIPPOAgent],
) -> None:
    if set(agents) != {spec.name for spec in ACTOR_NETWORK_SPECS}:
        raise ValueError("actor-local IPPO agent set does not match locked v0.1 nodes")

    parameter_ids: list[int] = []
    model_ids: list[int] = []
    optimizer_ids: list[int] = []
    for agent in agents.values():
        model_ids.append(id(agent.network))
        optimizer_ids.append(id(agent.updater.optimizer))
        parameter_ids.extend(id(parameter) for parameter in agent.network.parameters())

    if len(model_ids) != len(set(model_ids)):
        raise ValueError("actor networks must be distinct")
    if len(optimizer_ids) != len(set(optimizer_ids)):
        raise ValueError("actor optimizers must be distinct")
    if len(parameter_ids) != len(set(parameter_ids)):
        raise ValueError("actor parameters must not be shared")
