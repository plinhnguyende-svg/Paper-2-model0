# AI Actor-Local PPO Core Result v0.1

## Scope

This milestone implements the neural-network and PPO optimization core required by the locked AI specification.

It does **not** connect PPO to full Model 0 training, does not run the pre-registered training seeds, and does not produce learned checkpoints or performance results.

## Actor-local networks

Six distinct learnable agents are defined:

- R1, R2, R3: observation dimension 4;
- BQ: importer pre-revelation procurement, observation dimension 6;
- E1, E2: exporter readiness, observation dimension 7.

Every agent has:

- a feed-forward Gaussian policy network;
- a separate local value network;
- hidden layers 64 and 64 with tanh activation;
- one latent continuous action;
- learned log standard deviation.

No importer-allocation network exists.

No centralized critic exists.

No parameter or optimizer object is shared across actors.

The same training seed maps deterministically to the same actor-specific initialization convention across N, S, and F because the agent factory has no regime argument.

## Initialization convention

For the implementation core:

- PyTorch default Linear initialization is used;
- initial `log_std = 0`, corresponding to unit latent-action standard deviation;
- actor-specific initialization seeds are deterministically derived from the pre-registered training seed.

This convention is fixed at implementation review before full training.

## Actor-local rollout storage

`ActorRolloutBuffer` stores only:

- encoded local observation;
- latent action;
- log probability;
- team reward;
- local critic value;
- terminal flag.

It has no field for raw simulator state, regime label, scenario object, or another actor's observation.

## PPO update

The update implements the locked v0.1 hyperparameters:

[
gamma=1,qquad
lambda_{GAE}=0.95,qquad
epsilon_{clip}=0.20,
]

[
c_V=0.50,qquad
c_H=0.01,qquad
|
abla|_{max}=0.50,
]

with Adam learning rate (3	imes10^{-4}), minibatch size 64, and 10 epochs.

The actor-local loss is

[
L
=
L_{policy}
+
0.50L_{value}
-
0.01H.
]

Advantages are the pre-specified GAE quantities and are **not silently normalized** in this implementation.

Non-finite rollout data, loss, or gradient norm is treated as an implementation failure.

## Tests

The unit suite verifies:

- exactly six learnable nodes and no importer-allocation AI node;
- actor/critic output shapes;
- deterministic evaluation uses the policy mean;
- wrong local observation dimensions are rejected;
- no parameter/optimizer sharing;
- same training seed reproduces the same actor-specific initialization convention;
- distinct actors use distinct parameter objects;
- locked PPO hyperparameters cannot be silently changed;
- GAE terminal behavior at (gamma=1);
- rollout buffer contains only actor-local PPO quantities;
- one synthetic PPO optimization step is finite and changes the local model;
- non-finite training data is rejected.

The synthetic update is a software unit test only. It is not a Model 0 training experiment.

## Gate decision

[
oxed{
	ext{Actor-local PPO core implemented; full environment training remains blocked pending CI/review.}
}
