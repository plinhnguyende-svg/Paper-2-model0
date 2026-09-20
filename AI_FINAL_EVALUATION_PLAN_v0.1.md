# AI Final Evaluation Plan v0.1

**Status:** PLAN ONLY / NO FINAL EVALUATION AUTHORIZED BEFORE CHECKPOINT-REGISTRY FREEZE

## 1. Frozen evaluation design

After the post-training checkpoint registry is merged, final evaluation uses:

\[
T=1000,\qquad Warmup=200,
\]

with 200 held-out exogenous replications generated from evaluation master seed:

\[
52001.
\]

The same scenario path is reused across:

\[
N\text{-RuleBased},\
S\text{-RuleBased},\
F\text{-RuleBased},\
N\text{-AI},\
S\text{-AI},\
F\text{-AI}.
\]

Each of the five frozen AI training-seed policies is evaluated on the same 200
scenario replications.

No evaluation scenario may appear in training.

## 2. Required run count

RuleBased outcomes are generated once per regime/scenario:

\[
3\times200=600.
\]

AI outcomes are generated for each regime, frozen training seed, and scenario:

\[
3\times5\times200=3000.
\]

Total Model 0 trajectories:

\[
\boxed{3600}.
\]

Repeated RuleBased outcomes must not be treated as five independent
observations merely because they are paired with five AI seeds.

## 3. AI evaluation semantics

Final AI evaluation uses:

- the exact episode-1000 checkpoint in the frozen registry;
- deterministic Gaussian policy mean;
- no exploration noise;
- no learning;
- no optimizer update;
- no running-normalization fit;
- no checkpoint selection;
- no seed exclusion based on training-stability status.

Before loading a checkpoint, evaluation must verify its SHA-256 against the
frozen registry.

## 4. Primary outcomes

The five confirmatory outcomes are:

1. service level;
2. waste share of terminal outflow;
3. importer procurement bullwhip;
4. mean total inventory;
5. mean absolute target-allocation gap averaged across exporters.

Secondary outcomes:

- retail-order bullwhip;
- total lost sales;
- total waste;
- mean absolute stock-allocation gap averaged across exporters.

## 5. Primary estimands

For each outcome \(Y\):

\[
\Gamma_V(Y)
=
(Y_{S,AI}-Y_{N,AI})
-
(Y_{S,RB}-Y_{N,RB}),
\]

\[
\Gamma_H(Y)
=
(Y_{F,AI}-Y_{S,AI})
-
(Y_{F,RB}-Y_{S,RB}).
\]

There are:

\[
5\text{ outcomes}\times2\text{ interactions}=10
\]

confirmatory outcome-estimand combinations.

No universal N/S/F or AI/RuleBased ranking is pre-specified.

## 6. Raw evaluation panel

The evaluation runner should write one immutable row per treatment-policy
scenario outcome with, at minimum:

- scenario index and scenario id;
- evaluation scenario seed;
- regime;
- decision architecture;
- AI training seed (null for RuleBased);
- all primary outcomes;
- all secondary outcomes;
- frozen checkpoint SHA for AI rows;
- final evaluation code/source SHA.

The panel must preserve scenario pairing explicitly.

## 7. Uncertainty

Use the pre-registered hierarchical bootstrap with 10,000 resamples:

1. resample the five AI training seeds with replacement;
2. resample the 200 scenario ids with replacement;
3. preserve all treatment outcomes for each sampled scenario;
4. recompute \(\Gamma_V\) and \(\Gamma_H\).

Report means, 95% bootstrap confidence intervals, and between-training-seed
dispersion.

If formal significance statements are made, apply Holm adjustment across the
10 confirmatory tests.

## 8. Implementation sequence

\[
\boxed{
\text{checkpoint registry freeze}
\rightarrow
\text{evaluation scenario generator + checkpoint loader}
\rightarrow
\text{deterministic 6-treatment runner}
\rightarrow
\text{metric/interaction tests}
\rightarrow
\text{hierarchical bootstrap tests}
\rightarrow
\text{evaluation dry-run}
\rightarrow
\text{final evaluation freeze}
}
\]

No held-out evaluation result should be generated before the evaluation runner
and estimand code are separately reviewed and frozen.

