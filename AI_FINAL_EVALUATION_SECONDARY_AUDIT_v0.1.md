# AI Final Evaluation Secondary / Exploratory Audit v0.1

**Status:** R2 EXPLORATORY RESULTS CANDIDATE

## 1. Scope and provenance

R2 reads the already frozen 3,600-row panel and does not generate new trajectories.

Hard upstream anchors:

- results freeze: `7ea4ff9099525d1ee221905380f665f6d7627ff3`;
- R1 interpretation freeze: `ece7fd704e0e3151e3a5ef02bf660a9d5e343c8b`;
- panel JSONL SHA-256: `6ed8bbd779bf25f6f7370ee2e27439ce18915be98a9169d10dd1f08f6cf8c00c`;
- frozen evaluator: `9e42c4a39e6bc8be94d1ed44e993899e4d916481`;
- pre-held-out analysis code blob: `d85cc1b9f673d0ecd801f9eb12142e9e861aecc2`.

The same pre-held-out `panel_arrays` + `paired_bootstrap` implementation is used for the four registered secondary metrics. No new inference method is introduced.

## 2. Secondary absolute means

| Exploratory outcome | RB-N | RB-S | RB-F | AI-N | AI-S | AI-F |
|---|---:|---:|---:|---:|---:|---:|
| retail-order bullwhip | 3.204638 | 3.365473 | 2.960954 | 27.380898 | 36.849399 | 46.527073 |
| total lost sales | 255.806215 | 417.822711 | 218.852303 | 3172.694133 | 6610.510661 | 2807.099587 |
| total waste | 813.087318 | 1575.848125 | 928.688865 | 742.839576 | 1444.319058 | 1662.893886 |
| stock-allocation gap | 3.802331 | 5.673846 | 0.000000 | 71.855523 | 54.822294 | 49.661964 |

These values are descriptive. They do not alter R1's primary interpretation.

## 3. Exploratory N -> S interactions

| Outcome | RB S-N | AI S-N | Gamma_V | exploratory 95% interval |
|---|---:|---:|---:|---:|
| retail-order bullwhip | 0.160834 | 9.468501 | 9.307667 | [-28.174666, 47.363115] |
| total lost sales | 162.016497 | 3437.816528 | 3275.800031 | [-180.392076, 6813.859241] |
| total waste | 762.760807 | 701.479482 | -61.281325 | [-2024.010327, 2173.201345] |
| stock-allocation gap | 1.871515 | -17.033230 | -18.904744 | [-49.059334, -2.075621] |

The stock-allocation-gap exploratory interval lies below zero. This is not promoted to a confirmatory finding.

## 4. Exploratory S -> F interactions

| Outcome | RB F-S | AI F-S | Gamma_H | exploratory 95% interval |
|---|---:|---:|---:|---:|
| retail-order bullwhip | -0.404518 | 9.677674 | 10.082192 | [-36.527291, 45.670008] |
| total lost sales | -198.970409 | -3803.411074 | -3604.440665 | [-8664.310721, -96.279457] |
| total waste | -647.159259 | 218.574829 | 865.734088 | [-1875.507542, 3297.893636] |
| stock-allocation gap | -5.673846 | -5.160330 | 0.513516 | [-22.900361, 36.090899] |

The total-lost-sales exploratory interval lies below zero. This remains exploratory and cannot rewrite the R1 confirmatory narrative.

## 5. Seed heterogeneity

Seed-specific interaction means remain highly heterogeneous for several downstream metrics.

For example, retail-order-bullwhip Gamma_V across seeds 41001-41005 is:

```
-31.050906, +84.193681, +17.450554, -43.845132, +19.790138
```

Total-lost-sales Gamma_H is:

```
-2099.909940, -13468.609783, -179.664116, -3244.277897, +970.258410
```

No seed is dropped or reweighted.

## 6. Relation to R1

R2 is supporting/exploratory evidence only. The R1 interpretation lock remains authoritative:

- primary results remain the five pre-registered primary outcomes;
- R2 does not create a new headline estimand;
- secondary results do not justify changing primary wording after the fact;
- finite-training-budget and 1/15 stability disclosures remain binding.

## 7. Next gate

If this R2 package is reviewed and frozen, the next admissible layer is a manuscript-facing results presentation package:

```
R3 = reproducible tables + figures
     with explicit PRIMARY / EXPLORATORY labeling
```

R3 must read from frozen R1 and R2 registries and must not recompute or modify scientific results.
