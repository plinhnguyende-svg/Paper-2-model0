# Warm-up Convergence Result v0.1

## Run identity

- GitHub Actions run: 35333072314
- Branch: `verification-validation-v0.1`
- Head used by the validation run: `829197eb1c8fc618b7d45d7e4ba2e9779981ffe5`
- Artifact: `validation-warmup-35333072314`
- Artifact SHA-256: `0d1f14149ed55fd475d755eaa9c3d85abd233ff47d3d5ac70c6f7222e6badeee`
- Paired replications: 30
- Candidate warm-ups: 0, 50, 100, 200, 300, 400 days
- Fixed measurement window: 600 days
- Contrasts: S-N and F-S

## Diagnostic result

Across the 11 primary metrics and the two primary paired contrasts (22 metric-contrast combinations), the CI-based direction classification was unchanged across all six warm-up candidates.

For the comparison most relevant to the current baseline choice, the 95% confidence intervals at warm-up 200 and warm-up 400 overlapped for all 22 primary metric-contrast combinations.

Selected paired means:

| Metric | Effect | W=200 | W=400 |
|---|---|---:|---:|
| service_level | S-N | -0.006494 | -0.006631 |
| service_level | F-S | 0.008144 | 0.008083 |
| waste_share_of_terminal_outflow | S-N | 0.029381 | 0.029837 |
| waste_share_of_terminal_outflow | F-S | -0.024445 | -0.025055 |
| importer_procurement_bullwhip | S-N | -0.408821 | -0.454887 |
| importer_procurement_bullwhip | F-S | -2.864039 | -3.001048 |
| retail_order_bullwhip | S-N | 0.160510 | 0.152712 |
| retail_order_bullwhip | F-S | -0.409407 | -0.408477 |
| mean_abs_target_allocation_gap_1 | S-N | 0.926698 | 0.918832 |
| mean_abs_target_allocation_gap_1 | F-S | -4.834824 | -4.842415 |
| mean_total_inventory | S-N | 6.615767 | 6.618855 |
| mean_total_inventory | F-S | -1.628918 | -1.617767 |

## Interpretation

This first diagnostic does not show a warm-up-driven sign reversal in the primary N/S/F contrasts. The existing 200-day warm-up is therefore retained **provisionally** for the replication-sufficiency stage.

This is not an equivalence proof. Some effect magnitudes, especially importer-procurement bullwhip, still move across measurement windows. The next stage therefore tests whether those estimates stabilize as the paired replication count increases before the 200-day warm-up is locked for final robustness runs.

## Stage decision

[
\boxed{\text{Warm-up diagnostic: no directional instability detected; proceed to replication sufficiency.}}
]
