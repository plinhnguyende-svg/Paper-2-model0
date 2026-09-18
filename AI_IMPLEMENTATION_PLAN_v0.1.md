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
\boxed{\text{FULL-TRAINING RUNNER AUDITED; FREEZE PENDING MERGE}}
\]

The runner branch now contains the audited decision-boundary protocol,
256-day PPO chunking, deterministic checkpoint/resume state, common N/S/F
scenario-seed schedule, manifest binding, runtime fingerprint, and fail-fast
contract tests.

There is still no 15-run launcher and no scientific full-budget training.
Only after PR #8 is merged may a new launcher branch be created from that exact
merge commit.

No scientific AI performance claim is permitted at this gate.
