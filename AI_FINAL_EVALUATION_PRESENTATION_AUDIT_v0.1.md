# AI Final Evaluation Manuscript Presentation Audit v0.1

**Status:** R3 REPRODUCIBLE PRESENTATION CANDIDATE

## Scope

R3 is presentation-only. It reads two frozen registries and never reads the raw panel or calls the estimator.

- PRIMARY registry Git blob: `40d590f742c85f7e853bd3766a41fc335510b4b9`.
- EXPLORATORY registry Git blob: `3f99a7cca25e4ee7248d48e90d1db5aa45a08fe1`.
- R1 freeze: `ece7fd704e0e3151e3a5ef02bf660a9d5e343c8b`.
- R2 freeze: `b8806be6fe79c3981b8d82eb781634c31926611d`.

## Outputs

Committed outputs are generated into `outputs/manuscript_v0.1/`:

- PRIMARY CSV table;
- PRIMARY Markdown table;
- PRIMARY small-multiple interval SVG;
- EXPLORATORY CSV table;
- EXPLORATORY Markdown table;
- EXPLORATORY small-multiple interval SVG.

The two layers are never mixed without a visible layer label.

## Figure discipline

Outcomes use different units, so each outcome has its own x-scale. Gamma_V and Gamma_H are displayed within that outcome panel against a zero reference. No significance stars, p-values, or color-coded inferential labels are used.

## Scientific immutability

R3 does not modify:

- the 3,600-row panel;
- R1 or R2 registries;
- model / PPO / evaluator / workflow code;
- frozen point estimates;
- frozen interval endpoints;
- frozen seed means.

The only numerical transformation is display formatting and plotting-coordinate scaling.

## Gate after R3

After exact-head tests and review, R3 may be merged and frozen. The next layer is manuscript prose/results-discussion assembly using the R1 interpretation lock as the primary authority and R2 as exploratory support.
