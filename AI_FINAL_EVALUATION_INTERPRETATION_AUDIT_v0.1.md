# AI Final Evaluation Interpretation Audit v0.1

**Status:** R1 PRIMARY-RESULT SYNTHESIS CANDIDATE / NO SECONDARY OUTCOME INTERPRETATION

## 1. Frozen input audit

R1 reads the completed result package only. It does not retrain, resimulate, select checkpoints, alter the 3,600-row panel, or redefine the primary estimands.

Frozen anchors:

- result freeze SHA: `7ea4ff9099525d1ee221905380f665f6d7627ff3`;
- scientific run: `35531760845`, attempt 1, SUCCESS;
- panel JSONL SHA-256: `6ed8bbd779bf25f6f7370ee2e27439ce18915be98a9169d10dd1f08f6cf8c00c`;
- frozen evaluator SHA: `9e42c4a39e6bc8be94d1ed44e993899e4d916481`;
- checkpoint-registry SHA-256: `0ca89c10fc3135c577aca67f6d2ae573b72281b430218674dad5734ce72c686a`;
- frozen primary-analysis source blob: `d85cc1b9f673d0ecd801f9eb12142e9e861aecc2`.

The R1 summarizer fails closed unless it sees exactly 3,600 rows, 200 scenarios, and the exact 18 treatment-policy keys per scenario.

## 2. Training-stability disclosure

The preregistered training criterion labeled only **1 of 15** AI runs as `training-stable`: N / seed 41003.

The remaining **14 of 15** runs are labeled `not stabilized under the pre-registered budget`.

No run is excluded, reweighted, retrained, or replaced in R1. All 15 frozen policies remain in the pooled and seed-level decomposition. Because all S and F policies are labeled not stabilized, no Gamma_V or Gamma_H seed contrast has both endpoint policies labeled training-stable.

The admissible wording is therefore **learned policies under the pre-registered finite training budget**, not converged or optimal policies.

## 3. Primary absolute means

AI means below pool all five frozen training seeds and all 200 held-out scenarios per regime.

| Primary outcome | RB-N | RB-S | RB-F | AI-N | AI-S | AI-F |
|---|---:|---:|---:|---:|---:|---:|
| service_level | 0.989343 | 0.982592 | 0.990881 | 0.867842 | 0.724626 | 0.883069 |
| waste_share_of_terminal_outflow | 0.033099 | 0.062617 | 0.037575 | 0.029355 | 0.109975 | 0.063671 |
| importer_procurement_bullwhip | 15.452542 | 15.104802 | 12.237882 | 61.348719 | 64.807565 | 142.442500 |
| mean_total_inventory | 54.054499 | 60.664613 | 58.953703 | 35.277774 | 29.938138 | 39.643948 |
| mean_abs_target_allocation_gap_exporter_average | 3.802331 | 4.827274 | 0.000000 | 71.860281 | 54.517625 | 49.471527 |

These are descriptive means only. They are not a new ranking criterion.

## 4. Vertical contrast decomposition: N -> S

By definition:

```
Gamma_V = (S_AI - N_AI) - (S_RB - N_RB)
```

| Primary outcome | RB S-N | AI S-N | frozen Gamma_V | frozen 95% bootstrap CI |
|---|---:|---:|---:|---:|
| service_level | -0.006750 | -0.143216 | -0.136466 | [-0.283873, 0.007512] |
| waste_share_of_terminal_outflow | 0.029518 | 0.080620 | 0.051102 | [-0.076916, 0.243060] |
| importer_procurement_bullwhip | -0.347740 | 3.458845 | 3.806585 | [-22.402632, 43.844764] |
| mean_total_inventory | 6.610114 | -5.339636 | -11.949750 | [-46.769036, 13.617622] |
| mean_abs_target_allocation_gap_exporter_average | 1.024943 | -17.342656 | -18.367599 | [-49.124749, -1.245426] |

The last interval lies below zero in the frozen percentile interval. R1 does not translate that fact into a p-value or significance claim.

## 5. Horizontal/full-transparency contrast decomposition: S -> F

By definition:

```
Gamma_H = (F_AI - S_AI) - (F_RB - S_RB)
```

| Primary outcome | RB F-S | AI F-S | frozen Gamma_H | frozen 95% bootstrap CI |
|---|---:|---:|---:|---:|
| service_level | 0.008289 | 0.158443 | 0.150154 | [0.004007, 0.361032] |
| waste_share_of_terminal_outflow | -0.025042 | -0.046305 | -0.021262 | [-0.227332, 0.112237] |
| importer_procurement_bullwhip | -2.866920 | 77.634935 | 80.501856 | [-11.242796, 160.210667] |
| mean_total_inventory | -1.710909 | 9.705810 | 11.416719 | [-8.553010, 30.076282] |
| mean_abs_target_allocation_gap_exporter_average | -4.827274 | -5.046099 | -0.218824 | [-24.078204, 36.036946] |

The service-level interval lies above zero in the frozen percentile interval. R1 does not label this "statistically significant."

## 6. Seed-specific Gamma_V decomposition

| Training seed | service | waste share | procurement bullwhip | total inventory | target-allocation gap |
|---|---:|---:|---:|---:|---:|
| 41001 | -0.027842 | -0.037304 | -4.916250 | -13.592228 | -5.808123 |
| 41002 | -0.323760 | 0.421281 | 81.956706 | 25.504228 | -79.754765 |
| 41003 | -0.000678 | -0.011221 | -30.266066 | -4.729603 | -0.744331 |
| 41004 | -0.363295 | -0.126892 | -5.628130 | -77.012547 | 0.257204 |
| 41005 | 0.033247 | 0.009648 | -22.113334 | 10.081402 | -5.787983 |

Seed-level dispersion is retained rather than hidden by the pooled mean.

## 7. Seed-specific Gamma_H decomposition

| Training seed | service | waste share | procurement bullwhip | total inventory | target-allocation gap |
|---|---:|---:|---:|---:|---:|
| 41001 | 0.087455 | 0.064488 | 218.966532 | 33.457363 | -13.563430 |
| 41002 | 0.561123 | -0.425684 | -75.774410 | -21.831724 | 70.775598 |
| 41003 | 0.007474 | 0.160881 | 113.070670 | 28.983290 | -27.333811 |
| 41004 | 0.135137 | 0.079236 | 29.622131 | 25.477774 | -26.099733 |
| 41005 | -0.040421 | 0.014767 | 116.624355 | -9.003108 | -4.872747 |

The large cross-seed spread for several downstream outcomes is part of the result and must remain visible in later figures/discussion.

## 8. R1 interpretation lock

At this gate the results support only a constrained descriptive synthesis:

- information architecture and decision architecture interact rather than producing a universal N/S/F or AI/RuleBased ordering;
- the target-allocation-gap interaction under N -> S and the service-level interaction under S -> F have frozen percentile intervals entirely on one side of zero;
- downstream waste, bullwhip and inventory interactions show materially wider uncertainty and seed heterogeneity;
- the training-stability result requires finite-budget language and rules out post-hoc seed selection.

These statements are interpretation constraints for the next writing/figure layer. They are not new hypotheses, p-values, significance declarations, or robustness claims.

## 9. Next admissible gate

After this PR is reviewed and frozen:

```
R2 = secondary / exploratory outcomes
     (retail-order bullwhip, total lost sales, total waste,
      stock-allocation gap)
```

R2 must remain separately labeled exploratory and may not rewrite the R1 primary narrative because a secondary outcome happens to look more favorable.
