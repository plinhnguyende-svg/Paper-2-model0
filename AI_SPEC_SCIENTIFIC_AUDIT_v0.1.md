# AI Specification Scientific Audit v0.1

## Scope

This audit reviews PR #4 before any AI training.

The review focuses on the five questions most likely to determine whether the later RuleBased-vs-AI comparison is scientifically interpretable.

## 1. Why IPPO?

**Issue:** A centralized critic could receive hidden simulator state and weaken the N/S/F information treatment even if actors execute with local observations.

**Resolution:** v0.1 uses actor-local IPPO. Actor and critic receive only the legal observation vector of that actor. PPO is used as a continuous-control benchmark, not as a claim of optimality.

**Residual limitation:** independent learning can create non-stationarity and credit-assignment difficulty. This is reported as a limitation rather than solved by giving the critic illegal information.

## 2. Should AI control every node?

**Issue:** Making importer allocation learnable would change the validated N/S/F mechanism itself. In the current institution, the importer has no legal exporter-specific differentiating information in N, and S/F allocation is already determined by verified active status.

**Resolution:** importer allocation is frozen as an institutional rule. AI changes only discretionary replenishment and exporter-readiness targets.

This preserves the causal interpretation:

\[
\text{information architecture fixed}
\quad+\quad
\text{decision logic changed}.
\]

Node-level ablations are explicitly non-confirmatory in v0.1.

## 3. Is the reward defensible?

**Issue:** Model 0 has no calibrated monetary holding, shortage, or profit parameters. Inventing them for AI training would create a new economic model. Conversely, an unbounded action space with only service/waste incentives could generate artificial inventory accumulation.

**Resolution:** the cooperative reward uses only physical lost sales and waste plus a terminal leftover penalty. Inventory/readiness/bullwhip remain evaluation outcomes, not reward targets. Learnable targets are bounded using shelf-life and procurement scales.

**Interpretation:** this is a cooperative operational-control benchmark, not supplier-profit optimization.

## 4. Is the training budget arbitrary?

**Issue:** Any finite budget is partly a computational design choice. Extending training only when an undesirable result appears would create researcher degrees of freedom.

**Resolution:** five seeds, 1000 episodes, and all PPO hyperparameters are fixed before training. No hyperparameter search, early stopping, best-checkpoint selection, or post-hoc budget extension is allowed.

Training stability is reported using a pre-specified final-window diagnostic. Failure to stabilize is reported as a result of the training protocol rather than repaired post hoc.

## 5. Is the paired factorial estimand clean?

**Issue:** Simply comparing AI vs RuleBased does not answer whether AI changes the value of information.

**Resolution:** the primary estimands are the interaction contrasts

\[
\Gamma_V(Y)=
(Y_{S,AI}-Y_{N,AI})
-
(Y_{S,RB}-Y_{N,RB}),
\]

and

\[
\Gamma_H(Y)=
(Y_{F,AI}-Y_{S,AI})
-
(Y_{F,RB}-Y_{S,RB}).
\]

The same held-out exogenous scenario is used across all six treatments. AI training-seed uncertainty and scenario uncertainty are separated by hierarchical bootstrap.

## Additional blocking issues found and resolved

### Forecast-state ambiguity

The engine requires updated forecast state after retailer/importer replenishment decisions. The earlier draft specified only the AI target action and did not say how forecast state evolves.

**Resolution:** the exponential-smoothing forecast transition remains fixed and identical to RuleBased. AI chooses the target, not the forecast update.

### Unbounded target actions

The earlier softplus targets were unbounded.

**Resolution:** v0.1 uses sigmoid-bounded targets:
- retailer/importer target inventory positions are bounded by one shelf-life of mean demand;
- exporter readiness is bounded by current procurement requirement.

### Learnable importer allocation

The earlier draft allowed two importer allocation logits. With symmetric exporters and no differentiating legal information, that permits arbitrary label-based asymmetry and changes the treatment-defining allocation rule.

**Resolution:** importer allocation is no longer learnable in v0.1.

### Markdown/YAML inconsistency

The earlier Markdown table still displayed \(\gamma=0.99\) while YAML and prose used \(\gamma=1.0\).

**Resolution:** Markdown and YAML now both specify \(\gamma=1.0\).

## Audit disposition

No AI training should start until the revised specification passes CI and PR #4 is merged.

After merge, the merge commit becomes the sole base for the implementation branch.
