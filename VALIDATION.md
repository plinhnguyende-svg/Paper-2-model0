# Model 0 v0.1 validation snapshot

This snapshot documents the executable state supplied with the package.

## Automated tests

`pytest -q` result at packaging time:

```text
13 passed
```

The suite covers:

- V1 inventory non-negativity
- V2 global material conservation
- V3 shelf-life expiration
- V4 zero-demand behavior
- V5 perfect-availability neutrality: N = S = F
- V6 horizontal-information neutrality: hiding rival state from F collapses F to S
- V7 vertical-verification allocation isolation
- V8 FEFO age-bucket correctness
- common-random-number immutability
- regime-order invariance
- deterministic S/F readiness mechanism: Q=100, p=0.5, rival down gives S target 75 and F target 100

## Baseline computational smoke test

The included baseline was executed with:

- 50 paired replications
- 1,000 days per replication
- 200-day warm-up
- identical exogenous demand and availability paths across N/S/F within each replication
- p1 = p2 = 0.80
- shelf life = 7 days
- exporter-to-importer lead time = 2 days
- importer-to-retailer lead time = 1 day
- alpha = 0.30

Outputs are in `outputs/baseline/`.

These numbers are an implementation smoke test only. They are not calibrated empirical evidence and should not be reported as final Paper 2 findings before the planned validation, parameter audit, convergence analysis, and robustness experiments.
