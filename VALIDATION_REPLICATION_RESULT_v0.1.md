# Replication Sufficiency Result v0.1

## Run identity

- GitHub Actions run: 35333350226
- Branch: `verification-validation-v0.1`
- Head used by the validation run: `b78bc4bb8c7f7846a2bd115f9d9a42913628be73`
- Artifact: `validation-replications-35333350226`
- Artifact SHA-256: `37cc7f1239f6becccdfc357fd16b9019a73d11a345fcb6109fc435df8d64b5eb`
- Maximum paired replications: 200
- Nested checkpoints: 10, 20, 30, 50, 100, 200
- Baseline warm-up used: 200 days
- Contrasts: S-N and F-S

## Diagnostic result

Across the 11 primary metrics and two primary paired contrasts (22 metric-contrast combinations), the CI-based direction classification was unchanged at every replication checkpoint from n=10 through n=200.

For every one of the 22 primary metric-contrast combinations:

- the n=50 and n=200 95% confidence intervals overlap; and
- the n=100 and n=200 95% confidence intervals overlap.

Selected paired estimates:

| Metric | Effect | n=50 mean | n=50 CI half-width | n=200 mean | n=200 CI half-width |
|---|---|---:|---:|---:|---:|
| service_level | S-N | -0.006896 | 0.000531 | -0.006904 | 0.000253 |
| service_level | F-S | 0.008366 | 0.000607 | 0.008342 | 0.000328 |
| waste_share_of_terminal_outflow | S-N | 0.029791 | 0.000801 | 0.029542 | 0.000406 |
| waste_share_of_terminal_outflow | F-S | -0.025306 | 0.000916 | -0.024798 | 0.000539 |
| importer_procurement_bullwhip | S-N | -0.378470 | 0.127100 | -0.362284 | 0.060637 |
| importer_procurement_bullwhip | F-S | -2.939581 | 0.169322 | -2.889542 | 0.092535 |
| retail_order_bullwhip | S-N | 0.157043 | 0.027953 | 0.155123 | 0.014517 |
| retail_order_bullwhip | F-S | -0.424052 | 0.034962 | -0.414537 | 0.017215 |
| mean_abs_target_allocation_gap_1 | S-N | 0.902924 | 0.131235 | 0.960018 | 0.061969 |
| mean_abs_target_allocation_gap_1 | F-S | -4.814154 | 0.053837 | -4.840301 | 0.028531 |
| mean_total_inventory | S-N | 6.630603 | 0.041306 | 6.619053 | 0.025209 |
| mean_total_inventory | F-S | -1.687226 | 0.106694 | -1.684173 | 0.055349 |

## Interpretation

The direction of the primary N/S/F paired contrasts is not being created by a small replication count. Increasing the paired sample from 50 to 200 mainly tightens uncertainty rather than changing the qualitative contrast pattern.

This protocol did not pre-specify a metric-specific precision tolerance, so the run does **not** claim that n=50 is a mathematically minimal sufficient replication count. Instead:

- n=50 is retained as the working replication count for seed-stability and broad sensitivity experiments because it already matches the n=200 directional pattern and all primary n=50 confidence intervals overlap their n=200 counterparts;
- n=200 remains the high-precision reference for final baseline estimates when computational cost permits.

## Stage decision

[
\boxed{\text{Replication-count artifact not detected in primary contrast directions; proceed to seed stability.}}
]
