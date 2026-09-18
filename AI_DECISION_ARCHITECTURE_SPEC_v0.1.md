# AI Decision Architecture Specification v0.1

**Status:** LOCKED WHEN MERGED / PRE-IMPLEMENTATION. No AI training is authorized from the branch copy; the lock becomes effective only when this exact specification is merged into `main`.

**Frozen firewall base:** \`a1c0b15163d05fd4b02ccdcb1fa2843a421a07d3\`

This base contains the actor-isolated observation firewall frozen after PR #3.

## 1. Scientific purpose

The AI extension studies the factorial design

\[
\{N,S,F\}\times\{RuleBased,AI\}.
\]

The primary question is:

> Does the operational effect of verified information change when the same supply-chain institution is operated by learning-based autonomous decision policies instead of the validated RuleBased policies?

The information architecture remains \(N/S/F\). The AI treatment changes decision logic only. It does not change the physical network, FEFO mechanics, demand process, availability process, timing, or legal information rights.

The primary estimands are information-by-decision-architecture interactions, not a universal ranking of regimes and not a claim that AI is always better.

## 2. What is institutional and what is learnable

A key identification rule is that the **N/S/F importer allocation mechanism remains fixed**. It is part of the validated information-treatment institution and is not turned into an AI action.

The deterministic importer allocation rule therefore remains:

- \(N\): split \(Q_t\) equally across the two exporters; no same-period reallocation;
- \(S/F\): allocate \(Q_t\) equally across verified active exporters; allocate zero if none is active.

This prevents the AI treatment from silently redefining the N/S/F mechanism or exploiting arbitrary exporter labels.

The learnable decision nodes are:

1. Retailer 1 replenishment target;
2. Retailer 2 replenishment target;
3. Retailer 3 replenishment target;
4. importer pre-revelation procurement target;
5. Exporter 1 readiness target;
6. Exporter 2 readiness target.

The primary treatment is therefore a **system-level decision-architecture replacement at all discretionary replenishment/readiness nodes**, while the validated information/allocation institution remains fixed.

Node-level AI ablations are not part of the confirmatory v0.1 experiment. They require a separate pre-specified extension.

## 3. AI algorithm definition and rationale

The v0.1 AI benchmark is decentralized **Independent Proximal Policy Optimization (IPPO)** with actor-local critics.

This choice is pre-specified for four reasons:

1. the model already has decentralized actor-specific observation sets;
2. PPO naturally handles the continuous latent controls used for target decisions;
3. local critics avoid a centralized-critic information channel that could undermine N/S/F treatment isolation;
4. IPPO provides a common learning algorithm across all information regimes without changing network structure by regime.

This is a benchmark choice, not a claim that IPPO is globally optimal for the environment.

The v0.1 policies are feed-forward rather than recurrent. Recurrent policies are a later extension because hidden memory would require an additional information-leakage audit.

Each actor has a distinct mutable policy instance. Parameter sharing across actors is not allowed in v0.1.

### 3.1 Network architecture

For every learnable actor policy and value network:

\[
\text{input}\rightarrow64\rightarrow64\rightarrow\text{output},
\]

with \(\tanh\) activations.

Continuous latent actions use Gaussian policy heads with learned log standard deviation during training. Final evaluation uses the deterministic policy mean.

## 4. Observation encoding

Let retailer mean demand be \(\lambda_r>0\), and define aggregate mean demand

\[
\bar\lambda=\lambda_1+\lambda_2+\lambda_3.
\]

The v0.1 AI specification requires positive retailer mean demand because these constants are used as fixed normalization scales.

No running normalization fitted on final evaluation data is permitted.

The field \`current_day\` is excluded from learnable vectors so a policy cannot exploit the arbitrary finite evaluation horizon.

Known/value masks keep legal input dimensions identical across \(N,S,F\). The network structure therefore does not change with information regime; only legally available values change.

### 4.1 Retailer \(r\)

\[
o^{R_r}_t=
\left[
\frac{d_{r,t}}{\lambda_r},
\frac{I_{r,t}}{\lambda_r},
\frac{P_{r,t}}{\lambda_r},
\frac{f_{r,t-1}}{\lambda_r}
\right].
\]

These are current consumer demand, on-hand inventory, usable pipeline inventory, and previous forecast.

The vector is identical in \(N,S,F\).

### 4.2 Importer replenishment

Before current exporter availability is revealed:

\[
o^{B,Q}_t=
\left[
\frac{o_{1,t}}{\lambda_1},
\frac{o_{2,t}}{\lambda_2},
\frac{o_{3,t}}{\lambda_3},
\frac{f^B_{t-1}}{\bar\lambda},
\frac{I^B_t}{\bar\lambda},
\frac{P^B_t}{\bar\lambda}
\right].
\]

No current exporter-availability variable is present in any regime.

### 4.3 Exporter \(i\)

\[
o^{E_i}_t=
\left[
\frac{Q_t}{\bar\lambda},
a_{i,t},
\frac{I^E_{i,t}}{\bar\lambda},
p_j,
b_t,
k^j_t,
v^j_t
\right].
\]

Here:

- \(a_{i,t}\) is own current availability;
- \(p_j\) is known rival availability probability;
- \(b_t\) indicates whether the buyer uses verified state-contingent allocation;
- \(k^j_t\) is the legal-known mask for rival current availability;
- \(v^j_t\) is the rival availability value when known and is encoded as zero when unknown.

Thus:

\[
N,S:\quad k^j_t=0,
\]

while

\[
F:\quad k^j_t=1.
\]

The zero placeholder is never interpreted without its known-mask bit.

## 5. Forecast-state transition is held fixed

The validated RuleBased model stores retailer and importer forecasts as state variables. To avoid confounding learning with a different forecasting-state law, v0.1 keeps those forecast updates deterministic and identical to Model 0.

For retailer \(r\):

\[
f_{r,t}
=
\alpha d_{r,t}
+
(1-\alpha)f_{r,t-1}.
\]

For the importer:

\[
f^B_t
=
\alpha\sum_{r=1}^3 o_{r,t}
+
(1-\alpha)f^B_{t-1}.
\]

The AI does **not** choose the updated forecast. It observes the legal forecast state and chooses the operational target described below.

This rule ensures that a RuleBased-vs-AI comparison changes the control policy while preserving the existing forecast-state dynamics.

## 6. Action spaces and feasibility transforms

Unbounded softplus inventory targets are not permitted in v0.1 because they can create an artificial high-inventory solution under a non-monetary reward.

All target actions are therefore bounded by pre-specified operational scales.

### 6.1 Retailer replenishment

Retailer \(r\) outputs latent scalar \(z^{R_r}_t\in\mathbb R\).

Define

\[
S^{R_r,\max}=L\lambda_r,
\]

where \(L\) is shelf life in days.

The target inventory position is

\[
S^{R_r}_t
=
S^{R_r,\max}\sigma(z^{R_r}_t),
\]

where \(\sigma(\cdot)\) is the logistic sigmoid.

The replenishment order is

\[
O_{r,t}
=
\max\left\{
0,
S^{R_r}_t-I_{r,t}-P_{r,t}
\right\}.
\]

The cap corresponds to at most one shelf-life of mean demand in target inventory position. It is an explicit v0.1 action-domain assumption, not a physical capacity claim.

### 6.2 Importer replenishment

The importer outputs latent scalar \(z^{B,Q}_t\in\mathbb R\).

Define

\[
S^{B,\max}=L\bar\lambda.
\]

The importer target is

\[
S^B_t
=
S^{B,\max}\sigma(z^{B,Q}_t),
\]

and

\[
Q_t
=
\max\left\{
0,
S^B_t-I^B_t-P^B_t
\right\}.
\]

This decision is completed before current exporter availability is revealed.

### 6.3 Importer allocation remains deterministic

No AI allocation logits exist in v0.1.

After \(Q_t\) is formed, the validated N/S/F allocation rule is applied exactly as in the frozen RuleBased model.

Therefore the AI treatment cannot create an artificial allocation advantage by learning exporter labels or by changing the treatment-defining allocation mechanism.

### 6.4 Exporter readiness

If exporter \(i\) is unavailable:

\[
Y_{i,t}=0,
\qquad
Prepared_{i,t}=0.
\]

If exporter \(i\) is available, it outputs latent scalar \(z^Y_{i,t}\in\mathbb R\) and chooses

\[
Y_{i,t}
=
Q_t\sigma(z^Y_{i,t}).
\]

Hence

\[
0\le Y_{i,t}\le Q_t.
\]

Preparation remains mechanical:

\[
Prepared_{i,t}
=
\max\{0,Y_{i,t}-I^E_{i,t}\}.
\]

The AI chooses a readiness target; it does not choose a physical shipment or create inventory outside the existing model mechanics.

## 7. Training objective and reward

Model 0 does not contain calibrated prices, holding costs, shortage costs, or profit parameters. The v0.1 AI benchmark therefore does not invent a monetary objective.

It uses a common cooperative physical-efficiency reward:

\[
r_t
=
-
\frac{
LostSales_t+Waste_t
}{
\bar\lambda
}.
\]

At the terminal period, add:

\[
r_T^{terminal}
=
-
\frac{
OnHandInventory_T+PipelineInventory_T
}{
\bar\lambda
}.
\]

All agents receive the same scalar reward but do not receive another actor's hidden observation.

The following primary evaluation outcomes are deliberately excluded from the reward:

- bullwhip ratios;
- readiness/allocation gaps;
- service-level ratio;
- regime labels.

They remain evaluation outcomes rather than directly optimized targets.

Because target actions are bounded and perishable overstock generates waste, the reward cannot be improved through an unbounded inventory build-up.

This reward defines a **cooperative system-control benchmark**. It is not a model of self-interested supplier profit maximization.

## 8. PPO training protocol

The pre-registered v0.1 configuration is:

| Item | v0.1 value |
|---|---:|
| optimizer | Adam |
| learning rate | \(3\times10^{-4}\) |
| discount factor \(\gamma\) | 1.00 |
| GAE \(\lambda\) | 0.95 |
| PPO clip range | 0.20 |
| value-loss coefficient | 0.50 |
| entropy coefficient | 0.01 |
| maximum gradient norm | 0.50 |
| rollout length | 256 environment days |
| minibatch size | 64 |
| update epochs per rollout | 10 |
| hidden layers | 64, 64 |
| activation | tanh |

The discount factor is fixed at \(\gamma=1\) because the objective is an undiscounted finite-horizon physical-efficiency objective. This avoids making the terminal leftover-inventory penalty economically negligible solely because it occurs late in the episode.

No hyperparameter search is permitted in v0.1. Any change requires a new specification revision committed before training.

### 8.1 Training budget

Each \(N/S/F\) AI architecture is trained for exactly:

\[
1000\text{ episodes}\times1000\text{ days}
\]

for each of five pre-registered training seeds:

\[
41001,\ 41002,\ 41003,\ 41004,\ 41005.
\]

For a given training seed and episode index, \(N,S,F\) use the same exogenous demand/availability scenario-seed sequence.

Network architecture, initialization convention, optimizer, and hyperparameters are identical across regimes.

There is no early stopping and no best-checkpoint selection based on final evaluation outcomes. The fixed-budget final checkpoint is used.

### 8.2 Training sufficiency diagnostic

The 1000-episode budget is a pre-registered computational budget, not an assumption that every seed must mathematically converge.

For each training seed/regime:

1. compute mean episodic reward over episodes 601-800;
2. compute mean episodic reward over episodes 801-1000;
3. compute their relative change using the absolute earlier-window mean in the denominator with numerical epsilon;
4. regress episodic reward on episode index over episodes 801-1000 and report the slope with its 95% confidence interval.

A run is labelled **training-stable** when:

- the absolute relative change between the two 200-episode windows is at most 5%; and
- the 95% confidence interval for the final-window slope includes zero.

If these conditions fail, the run is reported as **not stabilized under the pre-registered budget**. The budget is not extended post hoc within v0.1.

A non-finite loss/action is an implementation failure and is not silently replaced by another seed.

## 9. Final paired evaluation design

Final evaluation starts only after all training runs and checkpoints are frozen.

Evaluation uses the validated Model 0 baseline horizon:

\[
T=1000,\qquad Warmup=200.
\]

Use 200 held-out exogenous replications generated from evaluation master seed:

\[
52001.
\]

These scenarios may not appear in training or development diagnostics.

For each evaluation scenario, the same exogenous path is reused across:

\[
N\text{-RuleBased},\
S\text{-RuleBased},\
F\text{-RuleBased},\
N\text{-AI},\
S\text{-AI},\
F\text{-AI}.
\]

Each of the five frozen AI training-seed policies is evaluated on the same 200 scenario replications.

No learning, exploration noise, parameter update, normalization fitting, or checkpoint selection is allowed during final evaluation.

## 10. Primary outcomes

The five primary outcomes are:

1. service level;
2. waste share of terminal outflow;
3. importer-procurement bullwhip;
4. mean total inventory;
5. mean absolute target-allocation gap averaged across the two exporters.

The fifth outcome is:

\[
\frac12
\left(
MeanAbsTargetGap_1+MeanAbsTargetGap_2
\right).
\]

Secondary outcomes include retail-order bullwhip, total lost sales, total waste, and mean absolute stock-allocation gap.

## 11. Primary estimands

For outcome \(Y\), define the vertical-information interaction:

\[
\Gamma_V(Y)
=
\left(Y_{S,AI}-Y_{N,AI}\right)
-
\left(Y_{S,RuleBased}-Y_{N,RuleBased}\right),
\]

and the horizontal-information interaction:

\[
\Gamma_H(Y)
=
\left(Y_{F,AI}-Y_{S,AI}\right)
-
\left(Y_{F,RuleBased}-Y_{S,RuleBased}\right).
\]

These are the confirmatory estimands because they ask whether the decision architecture changes the operational effect of information architecture.

Secondary contrasts are:

\[
Y_{R,AI}-Y_{R,RuleBased},
\qquad R\in\{N,S,F\},
\]

plus N-to-S and S-to-F information effects within AI.

No universal ranking is pre-specified.

## 12. Uncertainty, pairing, and multiplicity

For each AI training seed \(s\) and evaluation scenario \(k\), compute the paired interaction using that seed's AI outcomes and the RuleBased outcomes from the same scenario.

Uncertainty uses a hierarchical bootstrap with 10,000 resamples:

1. resample the five AI training seeds with replacement;
2. resample the 200 scenario IDs with replacement;
3. preserve all treatment outcomes belonging to a sampled scenario;
4. recompute the interaction estimand.

This design treats five as the number of independent training-seed realizations; it does not treat repeated RuleBased values across AI seeds as additional independent RuleBased simulations.

Report means, 95% bootstrap confidence intervals, and between-training-seed dispersion.

There are 10 confirmatory outcome-estimand combinations: five outcomes times \(\Gamma_V\) and \(\Gamma_H\).

The primary report emphasizes effect sizes and confidence intervals rather than a binary winner. If formal significance claims are made, Holm adjustment is applied across the 10 confirmatory tests.

## 13. Information-firewall requirements

The merged PR #3 firewall remains binding:

- no actor policy receives \`SupplyChainModel\` or \`ExogenousScenario\`;
- no rollout buffer stores hidden state not contained in that actor's legal observation;
- no centralized critic receives full simulator state;
- actor policy objects remain distinct;
- importer procurement remains pre-revelation in all regimes;
- N/S/F allocation remains the frozen deterministic mechanism;
- N and S exporter readiness cannot condition on rival current availability;
- no regime identifier is an AI input;
- final-evaluation scenarios are never used for training or model selection.

## 14. Why all discretionary nodes are changed together

The confirmatory treatment is deliberately a system-level decision-architecture treatment:

\[
RuleBased\rightarrow AI
\]

at all discretionary replenishment/readiness nodes.

Changing only one node would answer a different question: which local agent drives the effect. That is useful for mechanism decomposition but is not the primary factorial question.

Therefore node-level ablations are reserved for a separately pre-specified extension and must not be used to select or redefine the v0.1 headline result.

## 15. What is out of scope for v0.1

The following require a new specification:

- recurrent policies;
- centralized training with decentralized execution;
- actor parameter sharing;
- AI-controlled importer allocation;
- LLM or generative-agent policies;
- monetary profit/cost rewards;
- self-interested supplier objectives;
- online learning during final evaluation;
- hyperparameter search;
- post-hoc extension of the training budget;
- retraining separately for validation phase-map cells;
- changing the demand process, physical network, shelf-life mechanics, or N/S/F information architecture.

## 16. Specification lock and no-training gate

This specification is a lock candidate on the branch and becomes the locked v0.1 specification only when this exact audited version is merged into `main`.

It becomes locked only when:

1. scientific audit is complete;
2. Markdown and machine-readable specification agree;
3. contract tests and CI pass;
4. PR #4 is merged into \`main\`;
5. the resulting merge commit is recorded as the sole base for AI implementation.

Until then:

\[
\boxed{\text{NO AI TRAINING RUNS}}
\]

After lock, implementation must occur on a new branch created from the locked specification commit.
