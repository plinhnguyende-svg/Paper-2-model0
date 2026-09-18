# AI Implementation Plan v0.1

**Locked specification base:** `2af1c2f6e6f52c65576e00a33de65942bddd3c92`

This branch implements the frozen AI Decision Architecture Specification v0.1. It must not change the scientific specification silently.

## Sequential implementation gates

1. implement deterministic observation encoders and bounded action transforms;
2. preserve fixed exponential-smoothing forecast-state transitions;
3. keep importer allocation on the frozen N/S/F institutional rule;
4. implement actor-local policy/value networks and IPPO update code;
5. add unit tests for observation dimensions, action bounds, actor isolation, and deterministic evaluation mode;
6. add deterministic smoke-training tests on tiny horizons only to detect numerical/shape failures;
7. review CI and implementation audit;
8. only then run the pre-registered full training seeds and budget.

## Hard constraints

- no centralized critic;
- no recurrent policy;
- no parameter sharing;
- no regime label as input;
- no hidden simulator state in actor or critic observations;
- no AI-controlled importer allocation;
- no hyperparameter search;
- no change to training seeds, evaluation seed, training budget, reward, primary outcomes, or estimands without a new specification revision.

## Current gate

\[
\boxed{\text{SMOKE MILESTONE FROZEN; FULL-TRAINING RUNNER IMPLEMENTATION OPEN}}
\]

The corrected end-to-end smoke milestone has been reviewed and frozen. The
separate `ai-full-training-v0.1` branch is now reserved for implementing the
pre-registered full-training runner.

The runner itself must pass its own rollout-boundary, checkpoint/resume,
scenario-pairing, non-finite, and manifest tests before any five-seed ×
1000-episode training job is launched.

No scientific AI performance claim is permitted at this gate.
