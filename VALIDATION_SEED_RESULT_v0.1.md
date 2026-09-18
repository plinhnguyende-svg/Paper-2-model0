# Seed Stability Result v0.1

## Run identity

- GitHub Actions run: 35333685697
- Branch: `verification-validation-v0.1`
- Head used by the validation run: `740dd178626b39a6cf4095e54ef10fc6f9c2996d`
- Artifact: `validation-seeds-35333685697`
- Artifact SHA-256: `7fc215c86a9b47292c6c7f293dfbb5912a1e7d92c2fcd02f8e732181e1a4dbec`
- Master seeds: 20260917, 20260918, 20260919, 20260920, 20260921
- Paired replications per master seed: 50
- Baseline warm-up: 200 days
- Contrasts: S-N and F-S

## Diagnostic result

Across all five master seeds, every one of the 22 primary metric-contrast combinations retained the same CI-based direction classification.

Selected seed-level paired means:

| Metric | Effect | Seed 17 | Seed 18 | Seed 19 | Seed 20 | Seed 21 |
|---|---|---:|---:|---:|---:|---:|
| service_level | S-N | -0.006896 | -0.006754 | -0.006660 | -0.007251 | -0.006809 |
| service_level | F-S | 0.008366 | 0.008342 | 0.008112 | 0.008642 | 0.008005 |
| waste_share_of_terminal_outflow | S-N | 0.029791 | 0.029454 | 0.028712 | 0.029972 | 0.029420 |
| waste_share_of_terminal_outflow | F-S | -0.025306 | -0.024714 | -0.023801 | -0.025462 | -0.024718 |
| importer_procurement_bullwhip | S-N | -0.378470 | -0.414060 | -0.430976 | -0.346221 | -0.346402 |
| importer_procurement_bullwhip | F-S | -2.939581 | -2.927359 | -2.810706 | -2.837051 | -2.757585 |
| retail_order_bullwhip | S-N | 0.157043 | 0.139536 | 0.149682 | 0.148268 | 0.151797 |
| retail_order_bullwhip | F-S | -0.424052 | -0.401876 | -0.385936 | -0.401877 | -0.381753 |
| mean_abs_target_allocation_gap_1 | S-N | 0.902924 | 1.004679 | 1.068507 | 1.042620 | 1.037456 |
| mean_abs_target_allocation_gap_1 | F-S | -4.814154 | -4.861065 | -4.869063 | -4.842314 | -4.819287 |
| mean_total_inventory | S-N | 6.630603 | 6.626207 | 6.604969 | 6.562964 | 6.603877 |
| mean_total_inventory | F-S | -1.687226 | -1.734877 | -1.646745 | -1.713325 | -1.730576 |

## Interpretation

The primary paired-effect directions are not dependent on the single original master seed. Magnitudes do vary across master seeds, as expected under finite Monte Carlo sampling. The largest relative movement among the primary contrasts occurs for some smaller-magnitude effects such as S-N importer-procurement bullwhip, but its CI-based direction remains unchanged across all five master seeds.

The seed analysis therefore supports continuing to parameter sensitivity. It does not imply that one seed is representative of every possible stochastic realization; rather, it shows that the baseline contrast pattern is reproduced under several independent master streams.

## Stage decision

[
\boxed{\text{Seed-driven directional artifact not detected in the primary contrasts; proceed to parameter sensitivity.}}
]
