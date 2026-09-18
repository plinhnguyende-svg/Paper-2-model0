# Pre-Registered Full Training Runner Plan v0.1

**Status:** FINAL RUNNER AUDIT COMPLETE / FREEZE PENDING MERGE / FULL TRAINING NOT AUTHORIZED

**Frozen smoke base:** \`dadfec406647065a2055d31b5bbbc404c2dbefe6\`

This branch exists only to implement and test the pre-registered full-training
runner. It must not change the frozen scientific specification, N/S/F
institution, observation firewall, action bounds, reward definition, PPO
hyperparameters, or smoke-audited learning semantics.

## 1. Pre-registered training design

The runner must execute exactly:

\[
\{N,S,F\}
\times
\{41001,41002,41003,41004,41005\}
\]

with:

\[
1000\ \text{episodes per training seed/regime},
\qquad
1000\ \text{Model-0 days per episode}.
\]

For a fixed training seed and episode index, \(N,S,F\) must receive the same
exogenous demand/availability scenario seed.

No hyperparameter search, early stopping, best-checkpoint selection, or
post-hoc budget extension is permitted.

## 2. Locked PPO settings

The runner must use the already frozen PPO core:

- Adam learning rate \(3\times10^{-4}\);
- \(\gamma=1\);
- GAE \(\lambda=0.95\);
- clip range \(0.20\);
- value coefficient \(0.50\);
- entropy coefficient \(0.01\);
- max gradient norm \(0.50\);
- rollout length 256 Model-0 days;
- minibatch size 64;
- 10 PPO epochs per rollout.

The runner must reject configuration drift rather than silently accepting it.

## 3. Critical rollout-boundary requirement

The smoke audit established that Model 0 decision transition \(t\) receives:

\[
r_t
=
-
\frac{
OnHandWaste_t
+
TransitWaste_{t+1}
+
LostSales_{t+1}
}{
\bar\lambda
}
\]

for nonterminal transitions.

Therefore a 256-day rollout cannot be finalized immediately after the
day-255 action. Its final reward requires the **pre-action consequences at the
start of day 256**.

The full runner must not solve this by executing the day-256 action under the
old policy and then updating retroactively.

Before full training is allowed, the implementation must expose a tested
decision-boundary stepping protocol that separates:

1. start-of-day arrivals / transit waste;
2. consumer service / lost sales;
3. decision observation boundary;
4. AI actions and dispatch;
5. end-of-day on-hand aging / waste.

At a rollout boundary, the runner must be able to observe the next
start-of-day consequences needed to finalize the previous transition, compute
the bootstrap value for the next legal decision state, perform the PPO update,
and only then choose the next action.

This is a blocking correctness condition for the full runner.

## 4. Actor-local rollout semantics

Every actor remains on the common daily Model-0 clock.

For unavailable exporters:

- no actor action is sampled;
- readiness/preparation are forced to zero;
- the daily critic value/reward transition is retained;
- \`policy_active=false\` excludes that day from actor-policy, entropy, KL, and
  clipping terms.

No unavailable day may be removed from the GAE time sequence.

## 5. Episode and rollout boundaries

The 1000-day episode is partitioned into rollout chunks of at most 256 decision
transitions.

Expected transition counts are:

\[
256+256+256+232=1000.
\]

For a nonterminal chunk, GAE must bootstrap from the local critic value at the
next legal decision state.

For the final episode transition:

- \`done=true\`;
- \`last_value=0\`;
- the frozen terminal on-hand/pipeline penalty is included;
- no state from the next episode is used for bootstrap.

Buffers must be cleared only after their corresponding PPO update has
completed successfully.

## 6. Scenario-seed protocol

The full runner must generate a deterministic episode-seed schedule from the
training seed and episode index.

Requirements:

- the same episode seed is reused across N/S/F for the same training-seed /
  episode-index pair;
- no evaluation seed derived from master seed \`52001\` may enter training;
- the generated scenario is immutable within an episode;
- scenario ids and episode seeds are written to the manifest.

The runner must have a unit test proving N/S/F scenario-id equality for every
sampled episode index used in the test.

## 7. Checkpoint policy

Only the fixed-budget final checkpoint is the scientific training output.

Intermediate checkpoints may be written only for crash recovery and
convergence diagnostics. They must not be used to select the final policy.

A checkpoint must contain enough state to resume deterministically:

- all six actor/critic parameters;
- all six optimizer states;
- learned log standard deviations;
- actor-local action-generator states;
- PPO minibatch-shuffle generator states;
- training seed;
- regime;
- completed episode index;
- episode/scenario seed protocol version;
- runner/config/spec version identifiers.

Resume tests must demonstrate that uninterrupted and save/resume execution
produce the same next stochastic actions and the same subsequent update on a
small deterministic fixture.

## 8. Required training diagnostics

For every regime/training-seed run, record:

- episodic team reward;
- policy loss by actor;
- value loss by actor;
- entropy by actor;
- approximate KL by actor;
- clip fraction by actor;
- gradient norm by actor;
- transformed-action summaries;
- non-finite event count;
- fraction of active exporter decision days;
- scenario id / episode seed.

A non-finite action, loss, reward, critic value, or gradient is an
implementation failure. The run must stop; it must not silently substitute a
new seed.

## 9. Pre-registered training-stability diagnostic

After exactly 1000 episodes, for every training seed/regime:

1. compare mean episodic team reward over episodes 601--800 and 801--1000;
2. report absolute relative mean change;
3. regress episodic reward on episode index over 801--1000;
4. report slope and 95% confidence interval.

The pre-registered label \`training-stable\` requires:

- absolute relative mean change \(\le 5\%\); and
- final-window reward-slope 95% CI includes zero.

If not, report:

\[
\boxed{\text{not stabilized under the pre-registered budget}}
\]

and do not extend training post hoc.

## 10. Runner implementation gate before real training

The runner PR must pass deterministic tests for:

- exact 256/256/256/232 rollout partition;
- delayed transition-reward finalization at chunk boundaries;
- correct nonterminal critic bootstrap;
- terminal \`last_value=0\`;
- common N/S/F scenario-seed schedule;
- no evaluation-seed contamination;
- unavailable-exporter policy masking across chunk boundaries;
- actor-local buffer clearing after update only;
- checkpoint/resume determinism;
- fail-fast behavior on non-finite values;
- manifest completeness;
- no scientific full-budget training started from CI.

Only after that runner PR is reviewed and frozen may the pre-registered
five-seed × 1000-episode jobs be launched.

## Current gate

The final runner audit is recorded in `AI_FULL_TRAINING_RUNNER_AUDIT_v0.1.md`.

\[
\boxed{
\text{RUNNER FREEZE PENDING FINAL CI + MERGE}
\quad;\quad
\text{NO 15-RUN LAUNCHER}
\quad;\quad
\text{NO FULL TRAINING}
}
\]

After merge, the resulting merge commit is the sole allowed base for a
separate launcher branch.
