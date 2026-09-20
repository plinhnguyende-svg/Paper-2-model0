# AI Final Evaluation Interpretation Protocol v0.1

**Status:** R1 PRIMARY-RESULT INTERPRETATION LOCK

## 1. Frozen inputs

This layer may read only the result package and scientific outputs frozen before interpretation:

- result freeze ref: `ai-final-evaluation-results-v0.1-frozen`;
- result freeze SHA: `7ea4ff9099525d1ee221905380f665f6d7627ff3`;
- scientific evaluation run: `35531760845`, run attempt 1;
- frozen workflow SHA: `d121c59cf860584a3df51b48ec8f8fae53ffef6c`;
- frozen evaluator SHA: `9e42c4a39e6bc8be94d1ed44e993899e4d916481`;
- final panel `panel.jsonl` SHA-256: `6ed8bbd779bf25f6f7370ee2e27439ce18915be98a9169d10dd1f08f6cf8c00c`;
- frozen result-registry Git blob SHA: `40d590f742c85f7e853bd3766a41fc335510b4b9`;
- frozen training-registry Git blob SHA: `ded174d7c9ffd23d15f0ec53767861bf641b993b`;
- frozen primary-analysis source Git blob SHA: `d85cc1b9f673d0ecd801f9eb12142e9e861aecc2`.

No raw trajectory is regenerated in this layer.

## 2. R1 scope

R1 is restricted to the five pre-registered primary outcomes:

1. service level;
2. waste share of terminal outflow;
3. importer procurement bullwhip;
4. mean total inventory;
5. mean absolute target-allocation gap averaged across exporters.

Permitted descriptive quantities are:

- absolute RuleBased means under N, S and F;
- absolute AI means under N, S and F, pooled over all five frozen training seeds;
- AI absolute means by frozen training seed;
- within-architecture contrasts S-N and F-S;
- reproduction of the already-frozen primary interaction point estimates;
- five training-seed-specific interaction means;
- training-stability labels attached to the relevant frozen checkpoints.

The frozen 95% bootstrap intervals and between-seed SD are read from the result registry; this PR does not define a new uncertainty estimator.

## 3. Interpretation restrictions

R1 must not:

- exclude or down-weight a training seed because of performance or stability;
- select a checkpoint after observing held-out outcomes;
- extend the 1,000-episode training budget;
- run new held-out trajectories;
- modify the 3,600-row panel;
- modify the primary estimator or bootstrap;
- introduce a new p-value, significance test or multiple-testing rule;
- promote a secondary outcome to a confirmatory primary outcome;
- claim a universal N/S/F ordering or universal AI-over-RuleBased ordering;
- use `training-stable` as an inclusion criterion.

All 15 registered AI checkpoints remain in the descriptive decomposition. The stability status is metadata about the finite training budget, not a post-hoc selection rule.

## 4. Allowed statistical language

This layer reports estimates, interval endpoints and heterogeneity descriptively.

Allowed examples:

- "the frozen 95% bootstrap interval lies above zero";
- "the interval spans zero";
- "the pooled interaction is negative/positive";
- "seed-specific estimates are heterogeneous";
- "14 of 15 training runs were not stabilized under the pre-registered budget."

This layer does not use "statistically significant", "insignificant", "proves", "optimal", or "converged" unless a later separately reviewed inferential/convergence protocol supports those terms.

AI policies should be described as **learned policies under the pre-registered finite training budget**.

## 5. Mechanism discipline

The descriptive decomposition is intended to separate:

```
information architecture
        -> decision response
        -> direct allocation/readiness outcomes
        -> downstream service / waste / inventory / bullwhip
```

This is an interpretation framework, not a causal claim beyond the randomized/common-scenario simulation design already frozen.

## 6. Reproduction rule

The R1 summarizer must:

1. verify the exact panel SHA-256;
2. verify the exact result- and training-registry Git blob SHAs;
3. verify 3,600 rows, 200 scenarios and 18 treatment-policy rows per scenario;
4. verify the frozen evaluator and registry provenance on every row;
5. use all five AI training seeds;
6. reproduce the frozen Gamma_V / Gamma_H point estimates and seed means to numerical tolerance;
7. emit only the five primary outcomes.

A mismatch fails closed.

## 7. Gate after R1

Only after the R1 protocol, summary and audit are reviewed and frozen may the project open:

```
R2 = secondary / exploratory outcome analysis
```

R2 must remain explicitly separate from the confirmatory primary layer.
