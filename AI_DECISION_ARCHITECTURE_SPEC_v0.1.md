# AI Decision Architecture Specification v0.1

**Status:** DRAFT / PRE-TRAINING. No AI training is authorized until this specification is reviewed and merged.

**Frozen software base:** `a1c0b15163d05fd4b02ccdcb1fa2843a421a07d3`

That commit contains the merged actor-isolated observation firewall from PR #3.

## 1. Scientific purpose

The AI extension studies the factorial design

[
\{N,S,F\}\times\{RuleBased,AI\}.
]

The identification target is not "Is AI always better?" and not "Is more transparency always better?"

The primary question is:

> Does the operational effect of verified information change when the same supply-chain institution is operated by learning-based autonomous decision policies instead of the validated RuleBased policies?

The information architecture remains N/S/F. The AI treatment changes only the decision architecture.

## 2. Actor and decision boundaries

The primary AI treatment replaces the RuleBased decision logic at all currently exposed decision boundaries while preserving the same timing and information rights.

There are six actor-isolated policy instances:

- Retailer 1 policy;
- Retailer 2 policy;
- Retailer 3 policy;
- one Importer policy;
- Exporter 1 policy;
- Exporter 2 policy.

The Importer policy makes two sequential decisions in each period:

1. pre-revelation replenishment / procurement requirement;
2. post-revelation allocation.

The two decisions belong to the same importer actor. Retailer and exporter policy state is not shared across actors.

No policy receives a regime label, the raw `SupplyChainModel`, the `ExogenousScenario`, or any hidden state outside its typed observation.

## 3. AI algorithm definition

The v0.1 AI benchmark is **decentralized Independent Proximal Policy Optimization (IPPO)** with actor-local critics.

The design deliberately excludes a centralized critic. Both actor and critic for each policy may use only that actor's legal observation vector.

The v0.1 policies are feed-forward rather than recurrent. This keeps the treatment interpretable and avoids introducing hidden-state channels in the first AI benchmark. Recurrent policies are a later extension and require a separate specification revision.

Each policy uses its own parameters. No parameter sharing is allowed between retailers, between exporters, or across roles in v0.1.

### Network architecture

For every actor-specific policy and value network:

[
\text{input}\rightarrow64\rightarrow64\rightarrow\text{output},
]

with (	anh) activations in the two hidden layers.

Continuous latent actions use Gaussian policy heads with learned log standard deviation during training. Evaluation uses the deterministic policy mean.

## 4. Observation encoding

Define retailer mean demand by (lambda_r) and aggregate mean demand by

[
\bar\lambda=\lambda_1+\lambda_2+\lambda_3.
]

Quantities are normalized by these fixed model scales. No running normalization fitted on evaluation data is permitted.

The field `current_day` is intentionally excluded from the learnable vector so that the policy cannot exploit the finite evaluation horizon.

### 4.1 Retailer (r)

The learnable vector is

[
o^{R_r}_t=
\left[
\frac{d_{r,t}}{\lambda_r},
\frac{I_{r,t}}{\lambda_r},
\frac{P_{r,t}}{\lambda_r},
\frac{f_{r,t-1}}{\lambda_r}
\right].
]

These are current consumer demand, on-hand inventory, usable pipeline inventory, and previous forecast.

The vector is identical in N, S, and F.

### 4.2 Importer replenishment

Before current exporter availability is revealed, the importer receives

[
o^{B,Q}_t=
\left[
\frac{o_{1,t}}{\lambda_1},
\frac{o_{2,t}}{\lambda_2},
\frac{o_{3,t}}{\lambda_3},
\frac{f^B_{t-1}}{\bar\lambda},
\frac{I^B_t}{\bar\lambda},
\frac{P^B_t}{\bar\lambda}
\right].
]

No current exporter-availability variable is present in any regime.

### 4.3 Importer allocation

The post-revelation importer vector is

[
o^{B,X}_t=
\left[
\frac{Q_t}{\bar\lambda},
\frac{o_{1,t}}{\lambda_1},
\frac{o_{2,t}}{\lambda_2},
\frac{o_{3,t}}{\lambda_3},
\frac{I^B_t}{\bar\lambda},
\frac{P^B_t}{\bar\lambda},
k_{1,t},v_{1,t},k_{2,t},v_{2,t}
\right].
]

For exporter (i):

- (k_{i,t}=1) when current availability is legally known to the importer and (0) otherwise;
- (v_{i,t}\in\{0,1\}) is the availability value when known and is encoded as (0) when (k_{i,t}=0).

Therefore:

[
N:\quad k_{1,t}=k_{2,t}=0,
]

while

[
S,F:\quad k_{1,t}=k_{2,t}=1.
]

S and F expose the same current exporter state to the importer.

### 4.4 Exporter (i)

The learnable exporter vector is

[
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
]

Here (a_{i,t}) is own current availability, (p_j) is the known rival availability probability, and (b_t) indicates whether the buyer uses verified state-contingent allocation.

For rival current availability:

[
N,S:\quad k^j_t=0,
]

and

[
F:\quad k^j_t=1.
]

When rival availability is hidden, (v^j_t=0) is only a placeholder and the known-mask bit remains zero.

## 5. Action spaces and feasibility mapping

The policy outputs latent continuous actions. The environment applies deterministic feasibility transforms. The AI may optimize decisions but may not violate the institution or physical feasibility.

### 5.1 Retailer replenishment

Retailer (r) outputs one latent scalar (z^{R_r}_t\in\mathbb R).

The implied target inventory position is

[
S^{R_r}_t
=
\lambda_r\operatorname{softplus}(z^{R_r}_t).
]

The actual replenishment order is

[
O_{r,t}
=
\max\left\{
0,
S^{R_r}_t-I_{r,t}-P_{r,t}
\right\}.
]

This preserves the order-up-to interpretation while allowing the target to be learned.

### 5.2 Importer replenishment

The importer outputs one latent scalar (z^{B,Q}_t\in\mathbb R).

The learned importer target inventory position is

[
S^B_t
=
\bar\lambda\operatorname{softplus}(z^{B,Q}_t),
]

and the procurement requirement is

[
Q_t
=
\max\left\{
0,
S^B_t-I^B_t-P^B_t
\right\}.
]

This decision is completed before current exporter availability is revealed.

### 5.3 Importer allocation

The importer outputs two allocation logits

[
(z^X_{1,t},z^X_{2,t}).
]

Eligibility is regime-dependent but not AI-controlled.

In N, both exporters are eligible because current availability is unknown.

In S and F, verified inactive exporters are masked out. If no exporter is verified active, allocation is ((0,0)).

If at least one exporter is eligible, softmax is applied only over eligible exporters:

[
s_{i,t}
=
\frac{\exp(z^X_{i,t})}
{\sum_{j\in\mathcal E_t}\exp(z^X_{j,t})},
]

and

[
X_{i,t}=Q_t s_{i,t}.
]

Thus

[
X_{i,t}\ge0,
\qquad
\sum_i X_{i,t}=Q_t
]

whenever at least one exporter is eligible.

### 5.4 Exporter readiness

If exporter (i) is unavailable,

[
Y_{i,t}=0,
\qquad
Prepared_{i,t}=0.
]

If exporter (i) is available, it outputs latent scalar (z^Y_{i,t}\in\mathbb R) and chooses readiness target

[
Y_{i,t}
=
\bar\lambda\operatorname{softplus}(z^Y_{i,t}).
]

Preparation is then mechanically determined by

[
Prepared_{i,t}
=
\max\{0,Y_{i,t}-I^E_{i,t}\}.
]

The AI therefore chooses a target, not an unconstrained physical shipment.

## 6. Training objective and reward

Model 0 does not contain calibrated prices, holding costs, shortage costs, or profit parameters. The AI specification therefore does not invent a monetary objective.

The primary AI benchmark uses a common physical-efficiency team reward.

For each period,

[
r_t
=
-
\frac{
LostSales_t+Waste_t
}{
\bar\lambda
}.
]

At the terminal period, add

[
r_T^{terminal}
=
-
\frac{
OnHandInventory_T+PipelineInventory_T
}{
\bar\lambda
}.
]

All agents receive the same scalar team reward, but no agent receives another actor's hidden observation.

The scale (\bar\lambda) changes reward magnitude only; it does not change the objective.

The following evaluation outcomes are deliberately **not** included in reward:

- bullwhip ratios;
- readiness/allocation gaps;
- service-level ratio;
- regime labels.

They remain evaluation outcomes rather than directly optimized targets.

This reward defines a cooperative operational AI benchmark. It is not a model of self-interested supplier profit maximization.

## 7. PPO training protocol

The primary v0.1 training configuration is fixed before the first training run:

| Item | Locked v0.1 value |
|---|---:|
| optimizer | Adam |
| learning rate | (3\times10^{-4}) |
| discount factor (gamma) | 0.99 |
| GAE (lambda) | 0.95 |
| PPO clip range | 0.20 |
| value-loss coefficient | 0.50 |
| entropy coefficient | 0.01 |
| maximum gradient norm | 0.50 |
| rollout length | 256 environment days |
| minibatch size | 64 |
| update epochs per rollout | 10 |
| hidden layers | 64, 64 |
| activation | tanh |

The discount factor is fixed at \(\gamma=1\) because the v0.1 objective is an undiscounted finite-horizon physical-efficiency objective. This prevents the terminal leftover-inventory penalty from becoming economically negligible merely because it occurs late in the episode.

No hyperparameter search is permitted in v0.1. Any change requires a new specification revision committed before training.

### 7.1 Training budget

Each N/S/F AI architecture is trained for exactly

[
1000
]

episodes of

[
1000
]

days for each training seed.

The five pre-registered training seeds are:

[
41001,41002,41003,41004,41005.
]

For a given training seed and episode index, N, S, and F use the same exogenous demand and availability scenario seed sequence. Network initialization uses the same seed convention across regimes.

There is no early stopping and no "best checkpoint" selection based on evaluation outcomes. The fixed-budget final checkpoint is the policy used for final evaluation.

Intermediate checkpoints may be stored only for convergence diagnostics.

### 7.2 Training diagnostics

Before evaluation, every training run must report:

- episodic team reward trajectory;
- policy and value losses;
- entropy;
- non-finite action/loss count;
- distribution of transformed actions.

A run with non-finite numerical values is an implementation failure. It is not silently rerun with a new seed.

## 8. Paired final evaluation design

Final evaluation begins only after all training runs are complete and frozen.

The evaluation configuration uses the already validated Model 0 baseline:

[
T=1000,
\qquad
Warmup=200.
]

Final evaluation uses

[
200
]

held-out exogenous replications generated from master seed

[
52001.
]

These evaluation scenarios must not appear in training or development diagnostics.

For every evaluation replication, the same exogenous scenario is reused across:

[
N	ext{-RuleBased},
S	ext{-RuleBased},
F	ext{-RuleBased},
N	ext{-AI},
S	ext{-AI},
F	ext{-AI}.
]

For AI, each of the five frozen training-seed policies is evaluated on the same 200 scenario replications.

No learning, exploration noise, parameter update, normalization fitting, or checkpoint selection is allowed during final evaluation.

AI evaluation uses deterministic policy means.

## 9. Primary outcomes

The five primary outcomes are:

1. service level;
2. waste share of terminal outflow;
3. importer-procurement bullwhip;
4. mean total inventory;
5. mean absolute target-allocation gap averaged across the two exporters.

The fifth outcome is defined as

[
\frac12
\left(
MeanAbsTargetGap_1+MeanAbsTargetGap_2
\right).
]

Secondary outcomes include retail-order bullwhip, total lost sales, total waste, and mean absolute stock-allocation gap.

## 10. Primary estimands

For any outcome (Y), define the vertical-information interaction:

[
\Gamma_V(Y)
=
\left(Y_{S,AI}-Y_{N,AI}\right)
-
\left(Y_{S,RuleBased}-Y_{N,RuleBased}\right),
]

and the horizontal-information interaction:

[
\Gamma_H(Y)
=
\left(Y_{F,AI}-Y_{S,AI}\right)
-
\left(Y_{F,RuleBased}-Y_{S,RuleBased}\right).
]

These two difference-in-differences contrasts are the primary estimands because they directly test whether decision architecture changes the operational value of information architecture.

Secondary contrasts are:

[
Y_{R,AI}-Y_{R,RuleBased},
\qquad R\in\{N,S,F\},
]

plus the N-to-S and S-to-F information effects within the AI architecture.

No universal ranking of regimes is pre-specified.

## 11. Uncertainty and reporting

Final effects are computed at the paired replication level.

Uncertainty is reported with a hierarchical bootstrap using 10,000 resamples:

1. resample the five AI training seeds with replacement;
2. resample the 200 evaluation scenario IDs with replacement while preserving all treatment outcomes within a scenario.

Report means and 95% bootstrap confidence intervals.

The final report must also show between-training-seed dispersion. A favorable single training seed may not be selected as the headline result.

## 12. Information-firewall requirements

The merged PR #3 firewall remains binding.

The training implementation must satisfy all of the following:

- no actor policy receives `SupplyChainModel` or `ExogenousScenario`;
- no policy replay/rollout buffer stores hidden state that was not in that actor's legal observation;
- no centralized critic receives full simulator state;
- actor policy objects remain distinct;
- N importer allocation cannot condition on current exporter availability;
- N and S exporter readiness cannot condition on rival current availability;
- S and F importer information remains identical;
- the importer procurement decision remains pre-revelation in every regime;
- no regime identifier is an AI input.

## 13. What is explicitly out of scope for v0.1

The following require separate future specifications:

- recurrent policies;
- centralized training with decentralized execution;
- parameter sharing;
- LLM or generative-agent policies;
- monetary profit/cost rewards;
- self-interested supplier objectives;
- online learning during final evaluation;
- hyperparameter search;
- retraining separately for validation phase-map cells;
- changing the demand process, physical network, shelf-life mechanics, or N/S/F information architecture.

## 14. Specification lock and no-training gate

This document is **not locked merely because it exists on a branch**.

The specification becomes locked only when:

1. this specification and its machine-readable companion are reviewed;
2. CI on the specification PR passes;
3. the PR is merged into `main`;
4. the resulting merge commit is recorded as the AI-training base.

Until those conditions hold:

[
\boxed{\text{NO AI TRAINING RUNS}}
]

After lock, implementation must occur on a new branch created from the locked specification commit.
