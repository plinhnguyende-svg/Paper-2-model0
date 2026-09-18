# AI Pre-PPO Components Result v0.1

## Scope

This milestone implements only the deterministic components required before any PPO network or trainer is added.

Implemented:

1. deterministic observation encoders;
2. bounded latent-action transforms;
3. fixed exponential-smoothing forecast transitions;
4. contract tests for dimensions, masking, bounds, and RuleBased forecast equivalence.

No neural network, optimizer, replay/rollout buffer, learned weight, training loop, or performance result is included.

## Observation encoders

The encoder uses only typed actor observations already permitted by the frozen information firewall.

Dimensions are fixed as:

- retailer: 4;
- importer replenishment: 6;
- exporter readiness: 7.

The exporter vector uses a separate rival-known mask and rival-value bit, so N/S and F retain the same input dimension without leaking hidden rival availability.

Neither current day nor regime label is encoded.

## Bounded action transforms

The transforms implement the locked specification:

[
S^{R_r}_t=Llambda_rsigma(z^{R_r}_t),
]

[
S^B_t=Larlambdasigma(z^{B,Q}_t),
]

and, for an available exporter,

[
Y_{i,t}=Q_tsigma(z^Y_{i,t}).
]

Unavailable exporters are forced to zero readiness/preparation.

Importer allocation is intentionally absent from the AI transform layer because allocation remains the frozen N/S/F institutional rule.

## Forecast transitions

Retailer and importer forecast-state updates are implemented as deterministic adapters using the exact existing exponential-smoothing law.

AI latent actions therefore affect operational targets but do not alter the forecast-state transition.

## Test gate

The component tests verify:

- exact normalized observation values and dimensions;
- day/regime exclusion;
- hidden-vs-visible rival mask encoding;
- rejection of non-positive normalization scales;
- numerically stable sigmoid behavior;
- exact forecast-update equivalence with frozen RuleBased policies;
- retailer/importer target bounds;
- exporter readiness bound and unavailable forced-zero behavior;
- absence of AI importer-allocation actions.

## Gate decision

[
oxed{	ext{Pre-PPO deterministic components implemented; PPO trainer remains blocked pending CI/review.}}
]
