# Gate 20 — Robustness result

The Gate 19 higher-profit/lower-output result is conditional on all-output routing.
It disappears when the intermediary can pool a chosen portion and sell the remainder
outside at unchanged terms. The new output-floor theorem follows from nested
feasible choices, not from a finite simulation alone.

See [model and proofs](GATE20_PARTIAL_POOLING_PROOFS.md).

## Same synthetic example across three models

Assumptions: q=70,Q=100,eta=P=1,v=.55,b0=.50,beta=.25,c=.15,k=.01,g=.10,
unbounded working capital, source formula with a=.15,r=1.25. This remains an
H0-parameter counterfactual, not a deployed transaction or a calibrated producer.

| Outcome | Outside only | All-output routing (Gate 19) | Partial allocation (Gate 20) |
|---|---:|---:|---:|
| Production | 35.000000 | 30.960317 | 35.000000 |
| Pool deposit | 0 | 30.960317 | 22.049335 |
| Outside sale | 35.000000 | 0 | 12.950665 |
| Producer profit | 6.125000 | 6.421936 | 6.663262 |

The intermediary uses the surplus-maximizing pool lot and routes remaining supply
outside. Producer income rises but production does not: the pooling opportunity
is already saturated at baseline production. This is distinct from a binding
working-capital explanation.

## Sweep and verification

504 synthetic configurations use the SAME parameter grid as Gate 19.
Gate 19 has six negative-output cases relative to outside-only; Gate 20 has zero.
The theoretical output-floor result holds beyond that grid under its assumptions.
There are 12 selected partial-pooling cases. No producer-profit dominance violation
relative to the restricted all-output model occurs at numerical tolerance 1e-30.
All these counts are parameter-grid descriptions, not estimated market frequencies.

Eight tests cover the old counterexample, independent joint quantity/venue grid,
fee-potential telescoping, monotone premium, beta monotonicity, finance, beta-zero
intermediary participation and cases with no attractive pool opportunity.

For beta=1, surplus-maximizing routing is an explicit contract/tie-break convention:
the intermediary retains none of the incremental surplus and is otherwise indifferent.
For beta<1 it follows from intermediary margin maximization. The primary example
uses beta=.25 and does not rely on this endpoint convention.

```sh
python3 -m unittest discover -s tests -p 'test_gate20.py' -v
python3 scripts/gate20_partial_pooling.py --out results/gate20
```

The solver imports the committed Gate 19 analytical primitives. It uses high-precision
Decimal bisection; it is not directed interval arithmetic or an EVM emulator.

## Paper consequence

Do not lock a main contribution as "pooling reduces biochar production" based on
Gate 19. Preserve it as a restriction-dependent contrast, and use Gate 20 to show
why marketing flexibility changes transmission. A defensible current result is:
smart-contract monetization can change financial returns without proportionate
physical expansion, because participation, optimal pooled lot size, pass-through
and pre-production finance are separate mechanisms.

Actual on-chain transaction reconciliation, producer attribution, an optimal
functional fee mechanism and an endogenous governance equilibrium remain open.
