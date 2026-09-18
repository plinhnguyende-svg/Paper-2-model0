# AI Tiny Deterministic Smoke Result v0.1

## Corrected run identity

- Workflow: \`AI Smoke Training\`
- GitHub Actions run: \`35362030251\`
- Experiment head: \`2d1ab81c2b5d02001ba76bc0862ee7884a643cd7\`
- Artifact: \`ai-smoke-35362030251\`
- Artifact id: \`10555296536\`
- Artifact SHA-256: \`828e146735061fcb49f4ece736dcf8f36fac5872ea881eaa9d3923a7ec53386b\`
- Scenario id: \`33d3737fe65e521b\`
- Smoke training seed: \`41001\`
- Horizon: 8 days

This is the post-audit run. It supersedes the earlier smoke artifact because
reward timing and unavailable-exporter policy masking were corrected before
freeze.

## Corrected gate checks

For each of \(N,S,F\):

- all 8 Model 0 days complete;
- all six actor-local buffers retain exactly 8 daily transitions;
- the same deterministic exogenous scenario id is used;
- team transition rewards are finite;
- all six PPO updates are finite;
- all six local actor/critic modules show a parameter change after the tiny
  update because each exporter has active decision days in this scenario;
- importer allocation remains the frozen N/S/F institutional rule.

The deterministic availability path contains both active and inactive days for
each exporter. The test suite verifies that exporter policy masks exactly equal
own operational availability.

Across three regimes, the smoke harness executes 18 finite actor-local PPO
updates.

Normal CI run \`35362030216\` also passed:

- Python 3.12: 75 passed;
- Python 3.13: 75 passed.

## Reward-timing audit

Model 0 orders events within day \(t\) as:

\[
\text{receive due shipments}
\rightarrow
\text{serve consumer demand}
\rightarrow
\text{AI decisions}
\rightarrow
\text{dispatch}
\rightarrow
\text{age on-hand inventory}.
\]

Therefore \(\text{TransitWaste}_t\) and \(\text{LostSales}_t\) occur before the
day-\(t\) AI decisions, while \(\text{OnHandWaste}_t\) is measured after those
decisions.

The corrected decision-transition reward is:

\[
r_t
=
-
\frac{
\text{OnHandWaste}_t
+
\text{TransitWaste}_{t+1}
+
\text{LostSales}_{t+1}
}{
\bar\lambda
},
\qquad t<T-1.
\]

For the final decision transition:

\[
r_{T-1}
=
-
\frac{\text{OnHandWaste}_{T-1}}{\bar\lambda}
-
\frac{\text{OnHand}_T+\text{Pipeline}_T}{\bar\lambda}.
\]

Day-0 lost sales and day-0 transit waste are initial-condition outcomes. For a
fixed scenario and initial state they are policy-independent constants, so
excluding them from action credit assignment does not create a policy-selection
incentive.

## Rollout-semantics audit

PPO/GAE stays on the Model 0 daily clock. Every actor has one transition record
per environment day.

This matters for exporters: deleting unavailable days would create irregular
actor-specific time steps and would silently change the interpretation of
\(\gamma\) and GAE.

The implementation instead preserves the daily critic/reward timeline and uses
a separate \`policy_active\` mask.

## Unavailable-exporter audit

If exporter \(i\) is unavailable:

\[
Y_{i,t}=0,
\qquad
Prepared_{i,t}=0,
\qquad
PolicyMask_{i,t}=0.
\]

On such a day:

- no stochastic Gaussian action is sampled;
- a zero latent placeholder is stored only for tensor/day alignment;
- the local critic value is evaluated;
- team reward remains in the daily return sequence;
- policy loss, entropy, approximate KL, and clipping statistics exclude that
  sample.

A dedicated fully-masked-batch test verifies that actor parameters and learned
\`log_std\` stay unchanged while critic parameters may update.

## Reproducibility audit

Each actor has its own deterministic stochastic-action generator derived from
the training seed.

The test suite verifies that unrelated changes to the global PyTorch RNG do not
alter the actor's stochastic action stream.

## Smoke-only diagnostic totals

The corrected eight-day diagnostic totals are:

- \(N\): \(-11.0855355038\)
- \(S\): \(-10.9895267547\)
- \(F\): \(-10.9217917773\)

These numbers exist only to make the software run reproducible. They are not
research findings, treatment-effect estimates, evidence of convergence, or a
basis for ranking \(N,S,F\).

## Freeze interpretation

The corrected smoke run establishes that the implementation path is executable
with causally aligned reward timing and decision-right-aware PPO updates:

\[
\text{legal observation}
\rightarrow
\text{policy}
\rightarrow
\text{bounded action}
\rightarrow
\text{Model 0}
\rightarrow
\text{transition reward}
\rightarrow
\text{daily rollout}
\rightarrow
\text{GAE}
\rightarrow
\text{masked PPO update}.
\]

It does not establish policy quality or operational superiority.

## Gate decision

\[
\boxed{
\text{CORRECTED END-TO-END SMOKE PASSED; PR \#7 IS READY FOR FREEZE REVIEW.}
\]
