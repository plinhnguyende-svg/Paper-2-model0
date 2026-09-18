# AI Smoke Scientific/Implementation Audit v0.1

## Scope

This audit is the required pre-freeze review of PR #7. It focuses on:

1. reward timing;
2. rollout semantics;
3. unavailable-exporter learning behavior.

## 1. Reward timing audit

### Finding

In Model 0, each day executes consumer demand fulfillment and lost-sales
measurement **before** retailer, importer, and exporter decisions.

Therefore assigning \`LostSales_t\` to the policy action chosen later on day
\(t\) is a timing error.

### Resolution

Use decision-transition rewards:

\[
r_t
=
-
\frac{Waste_t+LostSales_{t+1}}{\bar\lambda},
\qquad t<T-1.
\]

For the final transition:

\[
r_{T-1}
=
-
\frac{Waste_{T-1}}{\bar\lambda}
-
\frac{OnHand_T+Pipeline_T}{\bar\lambda}.
\]

Day-0 lost sales are excluded because they occur before any AI action. For a
fixed scenario and initial condition this exclusion is a policy-independent
constant, so it does not create a policy-selection incentive.

### Audit disposition

Resolved before freeze.

## 2. Rollout semantics audit

### Finding

PPO/GAE should remain on the Model 0 daily clock. Skipping unavailable-exporter
days entirely would create actor-specific irregular time steps and ambiguous
reward aggregation.

### Resolution

Every actor retains one transition record per Model 0 day. Rewards and critic
values remain day-aligned, and terminal flags remain episode-clock aligned.

The exporter policy-active mask separates **time in the environment** from
**whether that actor actually had a decision right**.

### Audit disposition

Resolved before freeze.

## 3. Unavailable-exporter learning audit

### Finding

The first smoke wiring sampled an exporter policy even when
\`own_operational_availability=False\`. The physical transformer forced
readiness to zero, but PPO still treated the sampled latent action as if it had
caused the reward. This would create a spurious policy-gradient signal.

### Resolution

When exporter \(i\) is unavailable:

\[
Y_{i,t}=0,\qquad Prepared_{i,t}=0.
\]

The implementation now also enforces:

\[
PolicyMask_{i,t}=0.
\]

No stochastic actor action is sampled. A zero latent placeholder is stored for
aligned tensors, and only the local critic value is evaluated.

PPO policy loss, entropy, approximate KL, and clip fraction are calculated only
over samples with \`PolicyMask=1\`. Value loss continues to use the complete
daily timeline.

A dedicated test verifies that a fully masked batch changes critic parameters
but leaves actor parameters and learned \`log_std\` unchanged.

### Audit disposition

Resolved before freeze.

## 4. Reproducibility

Actor stochastic action streams use actor-local generators derived from the
training seed. Global PyTorch RNG calls therefore cannot silently perturb the
sampled action sequence.

## 5. Scientific boundary

This audit does not evaluate AI performance and does not compare N/S/F
outcomes. It only establishes correct causal timing and learning semantics for
the implementation.

Full pre-registered training remains blocked until the corrected PR passes both
normal CI and the dedicated smoke workflow and is then merged.
