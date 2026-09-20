# AI Final Evaluation Result Audit v0.1

**Status:** RESULTS FREEZE CANDIDATE. This file records the completed frozen evaluation and the outputs of the analysis code frozen before held-out execution. It does not add p-values, significance claims, post-hoc model changes, seed exclusions, or manuscript interpretation.

## Scientific execution provenance

- Run: `35531760845`, run number 1, attempt 1, event `workflow_dispatch`, conclusion `success`.
- Frozen workflow execution SHA: `d121c59cf860584a3df51b48ec8f8fae53ffef6c`.
- Frozen evaluator SHA: `9e42c4a39e6bc8be94d1ed44e993899e4d916481`.
- Frozen workflow blob SHA: `c5be85429f673b648fe19c11095e1ff2c2bf54e7`.
- Frozen checkpoint registry SHA-256: `0ca89c10fc3135c577aca67f6d2ae573b72281b430218674dad5734ce72c686a`.
- All 40 evaluate jobs completed successfully; the collector completed successfully after validating the exact 40-shard input set.

## Final panel audit

The final panel artifact is GitHub Actions artifact `10611323765` with ZIP digest `sha256:3ad57268f6c0be6629edf65d4d6cc4239b50094fc7ca0709509face72edc736c`. The contained `panel.jsonl` has SHA-256 `6ed8bbd779bf25f6f7370ee2e27439ce18915be98a9169d10dd1f08f6cf8c00c`.

The panel has exactly 3,600 rows: 200 held-out scenarios × 18 treatment-policy combinations. It contains 600 RuleBased rows and 3,000 AI rows. Each scenario contains N/S/F RuleBased plus N/S/F for all five frozen AI training seeds. There are no duplicate treatment rows, no missing scenario indices, no undefined/non-finite values in the nine registered metrics, RuleBased rows have no checkpoint SHA, AI rows map to 15 distinct checkpoint SHAs, and every row pins the frozen evaluator and checkpoint-registry provenance.

## Frozen analysis contract

The analysis source is `src/paper2_model0/ai/evaluation_analysis.py` at blob SHA `d85cc1b9f673d0ecd801f9eb12142e9e861aecc2`, under the preregistered design in `AI_FINAL_EVALUATION_PLAN_v0.1.md` at blob SHA `99327e2892d268d9f3528bca548d403ba893a854`.

For each of the five primary outcomes it reports `Gamma_V` and `Gamma_H`, using 10,000 crossed training-seed/scenario bootstrap draws with Monte Carlo seed 62001, percentile 95% intervals, and between-training-seed SD. No p-values or significance claims are produced.

## Primary interaction outputs

| Outcome | Estimand | Mean | 95% bootstrap CI | Between-seed SD |\n|---|---|---:|---:|---:|\n| service_level | Gamma_V | -0.13646551 | [-0.28387302, 0.0075124753] | 0.19076882 |\n| service_level | Gamma_H | 0.15015369 | [0.0040068335, 0.36103190] | 0.23965030 |\n| waste_share_of_terminal_outflow | Gamma_V | 0.051102356 | [-0.076916134, 0.24305992] | 0.21338492 |\n| waste_share_of_terminal_outflow | Gamma_H | -0.021262497 | [-0.22733177, 0.11223704] | 0.23210154 |\n| importer_procurement_bullwhip | Gamma_V | 3.8065852 | [-22.402632, 43.844764] | 45.014806 |\n| importer_procurement_bullwhip | Gamma_H | 80.501856 | [-11.242796, 160.21067] | 110.16924 |\n| mean_total_inventory | Gamma_V | -11.949750 | [-46.769036, 13.617622] | 39.294300 |\n| mean_total_inventory | Gamma_H | 11.416719 | [-8.5530098, 30.076282] | 25.072475 |\n| mean_abs_target_allocation_gap_exporter_average | Gamma_V | -18.367599 | [-49.124749, -1.2454257] | 34.430489 |\n| mean_abs_target_allocation_gap_exporter_average | Gamma_H | -0.21882444 | [-24.078204, 36.036946] | 40.758402 |\n
## Interpretation lock

These numbers are recorded as outputs of the already-frozen estimator. This result-freeze candidate must be reviewed for provenance/reproduction only. Scientific interpretation, robustness extensions, secondary-outcome analysis, and any formal inferential layer must be handled in later explicitly scoped gates and must not rewrite the frozen 3,600-row panel or the frozen primary estimator.
