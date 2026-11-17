# Gate 21 — Designer problem with partial-pooling response

This gate introduces a normative designer who chooses the actual source control
`depositFeeScale` before producer output, anticipating Gate 20 optimal routing.
It preserves smart-contract economic rules as the research object; commercial beta
and pre-production capital remain separate assumptions.

See [designer specification and proofs](GATE21_DESIGNER_PROOFS.md) and the
[topic/RQ/proof map in Vietnamese](GATE21_RESEARCH_MAP_VI.md).

## Computational design scope

Approved menu: 30 positive scales .01 through .30. Six known-state experiments:
three initial project shares under S0 ratio .99 and H0 parameter-substitution ratio
1.25. Each response is a continuous globally reduced producer/routing problem;
the outer designer search is exhaustive over the 30-value menu, NOT all functions
or a continuous scale interval. Other parameters and normative constraints are
declared before results in GATE21_DESIGNER_PROOFS.md.

| Benchmark | Project inventory / total | Reference scale | Selected scale | Modeled output at reference | Output at selected scale | Feasible menu values |
|---|---|---:|---:|---:|---:|---:|
| S0 real formula | 10 / 100 | .18 | .05 | 44.608810 | 45.787118 | 26 |
| S0 real formula | 50 / 100 | .18 | None | 42.997112 | N/A | 0 |
| S0 real formula | 70 / 100 | .18 | None | 41.815133 | N/A | 0 |
| H0 parameter counterfactual | 10 / 100 | .15 | .04 | 44.312390 | 45.722085 | 27 |
| H0 parameter counterfactual | 50 / 100 | .15 | None | 41.153403 | N/A | 0 |
| H0 parameter counterfactual | 70 / 100 | .15 | .21 (also .22 tied) | 35.000000 | 35.000000 | 2 |

All numbers are synthetic model outcomes. H0 substitution is not proof of deployed
source equivalence. Reference policies in the four high-share rows violate the
declared designer constraints, even though producer choices can remain profitable.
No-feasible-policy means this approved menu cannot meet both constraints in that
state. It does not mean production is zero or no feasible continuous parameter exists.

## Economic lessons

1. Lower scale weakly raises selected production in the source-real model, but is
   not automatically an admissible design: it can violate token-budget or inventory limits.
2. Fee receipts themselves need not increase with the scale: participation and lot
   size respond. A budget constraint must be evaluated, not assumed monotone.
3. The exact HHI constraint yields a maximum pooling quantity. If this lies below
   baseline credit supply, feasible policies cannot expand production under the
   current partial-routing model. Profits and fee allocation can still change.
4. A lowest feasible menu scale is a weak global output optimum within the menu;
   equal-output alternatives can coexist. None of this proves a unique optimal fee
   function, optimal governance or an observed environmental effect.

Eight tests check the algebraic inventory cap against direct accounting, response
ordering, increasing differences, budget-bound selection, a fee-revenue nonmonotonic
example, production plateaus, infeasible menus and input domains.

```sh
python3 -m unittest discover -s tests -p 'test_gate21.py' -v
python3 scripts/gate21_designer.py --out results/gate21
```

Outer enumeration covers 180 state-policy cases. The inner solvers use 75-digit
Decimal bisection and numerical boundary tolerances; this is not directed interval
arithmetic. Transaction reconciliation and producer attribution are unchanged open
workstreams. No new actual transaction sample or royalty measurement is claimed.
