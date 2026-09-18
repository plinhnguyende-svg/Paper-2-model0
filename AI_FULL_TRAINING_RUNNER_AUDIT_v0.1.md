# AI Full-Training Runner Final Audit v0.1

## Scope

This is the final pre-freeze audit of PR #8. No full-budget AI training is
authorized by this document.

The audit focuses on four questions:

1. Is the runner reproducible after interruption?
2. What state persists and what resets between training episodes?
3. Are checkpoints cryptographically tied to the run manifest they claim to
   resume?
4. Can the public/default scientific path drift from the pre-registered
   regimes, seeds, horizon, PPO settings, or 15-run design?

## 1. Reproducibility contract

A scientific checkpoint contains, for all six actors:

- actor/critic network state, including learned \`log_std\`;
- Adam optimizer state;
- actor-local stochastic action-generator state;
- PPO minibatch-shuffle generator state.

It also contains:

- regime;
- training seed;
- completed episode count;
- simulation-config hash;
- runner/checkpoint/scenario protocol versions;
- frozen smoke base;
- frozen AI specification base;
- SHA-256 of the matching run manifest.

The run manifest records the full source commit SHA and a runtime fingerprint:

- Python implementation/version;
- NumPy version;
- pandas version;
- PyTorch version;
- operating-system family;
- machine architecture;
- byte order.

Scientific resume requires the same config, regime, training seed, manifest
hash, and runtime fingerprint.

A deterministic two-episode test verifies:

\[
\text{episode 1}
\rightarrow
\begin{cases}
\text{continue directly}\\
\text{save}\rightarrow\text{load}
\end{cases}
\rightarrow
\text{episode 2}.
\]

The two paths match exactly for:

- next stochastic latent actions;
- actor observations;
- log probabilities;
- critic values;
- policy-active masks;
- Model 0 period trajectory;
- subsequent PPO update statistics;
- final network parameters;
- final Adam state;
- final actor action-RNG state;
- final PPO shuffle-RNG state.

## 2. Episode-to-episode state continuity

### Finding during final audit

Reusing one AI architecture across episodes originally retained all historical
\`DecisionRecord\` objects. This did not change the policy mathematically, but
a 1000-episode run would accumulate millions of stale trace objects and blur
episode ownership of diagnostics.

### Resolution

At the start of each new episode, the runner now clears **only** per-episode
decision traces.

The following learning state persists:

\[
\boxed{
\text{network}
+
\text{optimizer}
+
\text{action RNG}
+
\text{shuffle RNG}
}
\]

The following environment state resets by constructing a new Model 0 episode:

- retailer/importer/exporter physical inventories;
- shipment pipeline;
- retailer demand forecasts to their fixed initial values;
- importer order forecast to its fixed initial value;
- recorder and material-balance counters.

Tests verify that the physical/pipeline/forecast state is reset while the
learned state and stochastic continuation are not reinitialized.

This defines the intended episodic learning semantics:

\[
\boxed{
\text{learning state continues}
\quad;\quad
\text{physical episode state resets}
}
\]

## 3. Manifest/checkpoint semantics

### Finding during final audit

A checkpoint and a run manifest were previously validated separately. A valid
checkpoint could therefore be presented next to a different otherwise-valid
manifest.

### Resolution

For the scientific 1000-day training configuration, checkpoint creation now
requires the current run manifest.

The checkpoint stores:

\[
\boxed{
SHA256(\text{canonical run manifest})
}
\]

and scientific resume requires the exact matching manifest.

The checkpoint/manifest pair must agree on:

- regime;
- training seed;
- completed episode count;
- SimulationConfig hash;
- protocol versions.

A scientific checkpoint cannot be saved without a manifest.

Tiny deterministic unit fixtures remain separately identifiable and cannot
carry a scientific run-manifest hash.

## 4. Budget, seed, regime, and hyperparameter drift

The default/public \`BoundaryAwareEpisodeRunner\` path now validates the
pre-registered scientific contract before starting:

\[
\{N,S,F\}
\times
\{41001,41002,41003,41004,41005\},
\]

\[
T=1000\text{ days per episode},
\qquad
1000\text{ episodes per scientific run},
\]

with the frozen PPO hyperparameters.

The exact run-key registry is:

\[
3\times5=15
\]

and is tested as an exact tuple, not generated from user input.

The training scenario schedule remains regime-independent and injective:

\[
seed_{s,e}=1000s+e,
\qquad e=0,\ldots,999.
\]

All 5000 training-seed/episode pairs are tested collision-free, and evaluation
master seed \`52001\` is excluded.

PPO hyperparameters are validated against the locked v0.1 object, and contract
tests bind the runtime PPO values, training seeds, training budget, horizon,
information regimes, and evaluation seed back to the frozen machine-readable
YAML specification.

Tiny deterministic tests require an explicit test-fixture override. That
override is not a scientific training entry point and no 15-run launcher
exists in PR #8.

## 5. Reward-timing reconciliation with the frozen specification

The frozen specification defines the undiscounted physical objective from lost
sales, waste, and terminal leftover inventory.

The smoke audit established the actual Model 0 event order:

\[
\text{arrivals}
\rightarrow
\text{consumer service}
\rightarrow
\text{decision}
\rightarrow
\text{dispatch}
\rightarrow
\text{on-hand aging}.
\]

Therefore current-day transit waste and lost sales are pre-action outcomes,
while current-day on-hand waste is post-action.

The implementation assigns pre-action outcomes to the preceding decision
transition rather than to an action that has not yet occurred.

A regression test proves that the sum of transition rewards equals the frozen
undiscounted episode objective up to:

\[
\frac{
LostSales_0+TransitWaste_0
}{
\bar\lambda
},
\]

which is a fixed initial-condition constant before any AI action.

No reward component, coefficient, or evaluation outcome has been added.

## 6. Fail-fast behavior

The runner rejects non-finite:

- actor-distribution mean or standard deviation;
- sampled action;
- log probability;
- critic value;
- rollout data;
- transition reward;
- PPO batch;
- PPO loss;
- gradient norm;
- checkpoint network state;
- checkpoint optimizer state.

A failed scientific run is not silently replaced by another seed.

## 7. What PR #8 still does not contain

PR #8 contains no:

- 15-run launcher;
- full 1000-episode training execution;
- learned scientific checkpoint;
- training-stability result;
- RuleBased-vs-AI performance comparison;
- final evaluation run.

The branch therefore cannot produce the confirmatory AI result by itself.

## Freeze criterion

PR #8 is freeze-ready only if, at its final head:

1. normal CI passes on Python 3.12 and 3.13;
2. the dedicated AI smoke workflow passes;
3. no unresolved review thread remains;
4. the diff still contains no full-training launcher or scientific training
   output.

After merge, the merge commit becomes the sole frozen runner base for the
separate 15-run launcher branch.

\[
\boxed{
\text{FREEZE RUNNER FIRST}
\rightarrow
\text{IMPLEMENT LAUNCHER FROM THAT EXACT COMMIT}
}
\]
