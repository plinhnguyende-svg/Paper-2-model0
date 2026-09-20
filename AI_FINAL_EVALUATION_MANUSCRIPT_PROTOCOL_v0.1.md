# AI Final Evaluation Manuscript Prose Protocol v0.1

**Status:** R4 RESULTS + DISCUSSION PROSE LAYER

## 1. Frozen authorities

R4 is a prose-only layer. Its scientific authorities are frozen upstream packages:

- R1 PRIMARY interpretation freeze:
  `ai-final-evaluation-interpretation-v0.1-frozen`
  at `ece7fd704e0e3151e3a5ef02bf660a9d5e343c8b`.
- R2 EXPLORATORY freeze:
  `ai-final-evaluation-secondary-v0.1-frozen`
  at `b8806be6fe79c3981b8d82eb781634c31926611d`.
- R3 presentation freeze:
  `ai-final-evaluation-presentation-v0.1-frozen`
  at `a8e91934867714e81f2fd44b29c229c4d02c615c`.

R4 must not read or alter the raw 3,600-row panel, rerun any estimator, modify any frozen result, or create a new statistical test.

## 2. Authority hierarchy

The manuscript must follow this hierarchy:

1. **R1 controls the primary scientific narrative.**
2. **R2 may provide explicitly exploratory supporting evidence only.**
3. **R3 supplies display-formatted tables and figures only.**

If R2 appears more favorable than R1, R2 must not replace, reverse, or upgrade the R1 interpretation.

## 3. Required primary narrative

The Results and Discussion must preserve all four R1 locks:

- information architecture and decision architecture interact rather than producing a universal N/S/F or AI/RuleBased ordering;
- the PRIMARY target-allocation-gap Gamma_V interval lies below zero;
- the PRIMARY service-level Gamma_H interval lies above zero;
- downstream primary waste, bullwhip, and inventory interactions show wider uncertainty and seed heterogeneity.

The manuscript must retain the training-stability disclosure:

- 1 of 15 AI training runs met the preregistered stability criterion;
- 14 of 15 did not stabilize under the preregistered budget;
- no seed was excluded, reweighted, retrained, or replaced;
- AI policies are described as **learned policies under the pre-registered finite training budget**.

## 4. Exploratory firewall

The R2 findings on stock-allocation gap and total lost sales may be discussed only inside an explicitly labeled EXPLORATORY subsection or paragraph.

R4 must not describe an exploratory interval as confirmatory evidence, a primary result, or a reason to rewrite the R1 headline.

## 5. Statistical language

Permitted:

- "the frozen 95% interval lies above/below zero";
- "the interval spans zero";
- "the point estimate is positive/negative";
- "seed-specific estimates are heterogeneous";
- "the exploratory interval lies above/below zero."

Forbidden unless a future reviewed inferential layer is added:

- "statistically significant";
- "statistically insignificant";
- p-value claims;
- "proves";
- "converged policy";
- "optimal policy";
- universal "AI is better" or "full transparency is better" claims.

## 6. Manuscript-facing figures and tables

R4 may cite only frozen R3 outputs in `outputs/manuscript_v0.1/`.

PRIMARY and EXPLORATORY tables/figures must remain visibly distinct.

## 7. Discussion discipline

Managerial implications must be conditional:

- disclosure design should be evaluated jointly with the decision architecture that consumes the information;
- direct coordination metrics and downstream operating metrics should be assessed separately;
- finite-budget learning instability is an implementation risk, not a reason for post-hoc seed selection.

R4 must state that the findings are from the frozen Model 0 simulation environment and should not be presented as universal empirical facts.

## 8. Traceability

Every headline scientific claim in the prose must have an entry in
`experiments/ai_final_evaluation_manuscript_claim_registry_v0.1.json`
that identifies whether its authority is R1 PRIMARY or R2 EXPLORATORY.

## 9. Gate after R4

After exact-head review and freeze, manuscript prose may be integrated into a full paper draft. Any new robustness analysis, additional simulation, or inferential method must open a new scientific gate rather than being inserted into R4.
