# Gate 19 — Result and evidence status

Main deliverable: [Endogenous production model and proofs](GATE19_ENDOGENOUS_PRODUCTION.md).
This extends the Gate 18 fixed-premium producer module without claiming observed
producer royalties, blockchain superiority or a complete strategic market equilibrium.

## What changed

Marketed lot is x=eta*y. Total incremental monetization surplus is
S(y)=(P-v)eta*y-P*F(eta*y)-g, and the producer captures beta*max(0,S(y)).
The producer can always use the outside channel at baseline credit payment b0.
At zero production there is no transaction or gas cost. Liquidity remains fixed
before production, and every other pool-execution assumption is stated explicitly.

## Analytic results

1. Dynamic real-formula deposit cost is strictly convex in lot size on its log domain.
2. Outside and pool profit branches each have a unique maximizer; compare their
   maximum VALUES to obtain a global solution of the continuous production problem.
3. The realized objective is a maximum of two branches and need not be concave.
   Two distinct global production choices can tie at a channel-switch threshold.
4. Profitable pooling can raise producer profit while reducing output. A positive
   average monetization premium does not imply a positive marginal premium.
5. Producer profit is weakly increasing in beta under the fixed contract structure,
   but production need not be. On a selected interior pool branch its derivative
   has the sign of P-v-P*F'(eta*y).
6. The old frozen-premium solution is not generally an upper or lower bound:
   marginal fee curvature and fixed-gas dilution work in opposite directions.

## Explicit synthetic illustration satisfying the sufficient theorem conditions

Assume q=70,Q=100,eta=P=1,v=.55,b0=.50,beta=.25,c=.15,k=.01,g=.10,
unbounded working capital, and the source formula with a=.15,r=1.25.
These are SYNTHETIC economic inputs and an H0-PARAMETER COUNTERFACTUAL,
not a verified deployed transaction or estimates of a biochar project.

| Outcome | Outside-only | Pool option selected |
|---|---:|---:|
| Physical output units | 35.000000 | 30.960317 |
| Producer profit in assumed currency | 6.125000 | 6.421936 |

At outside output, S without gas is about .720680>0 and the marginal pooling
surplus is about -.290122<0. Thus the sufficient theorem conditions are met.
The selected pool output has positive total premium and calculator fee below lot
size. All other execution constraints are assumed; this is not mainnet feasibility proof.

## Computational verification

- Eight new tests: analytic fee derivatives against finite differences; an independent
  dense-grid float cross-check of global branch solutions; strict domain/special-branch
  behavior; lower-output/higher-profit counterexample; numerical channel tie;
  beta-zero production invariance with intermediary participation; cash and zero-output
  corners; closed-form flat-branch and fixed-gas selection checks.
- Scenario sweep: 504 synthetic configurations; 262 choose pool, including beta-zero
  cases where intermediary benefits but producer output does not change.
- Six grid cases have lower output than their outside-only benchmark despite
  choosing the pool option. This is a descriptive count in an assumed parameter grid,
  not a population incidence or empirical estimate.
- A separate detailed sufficient-condition example uses c=.15; the default sweep
  uses c=.10. Its first grid counterexample is consequently a different example
  (outside output 40 vs pool output 33.829635), not an inconsistent calculation.

Reproduce from repository root:

```sh
python3 -m unittest discover -s tests -p 'test_gate19.py' -v
python3 scripts/gate19_endogenous.py --out results/gate19
```

The solver uses an analytically proven global reduction plus high-precision numerical
bisection. It does not claim directed interval arithmetic. Numerical near-ties are
flagged; exact two-solution existence is established by the gas-threshold argument.

## What remains open

Actual historical transaction reconciliation and producer attribution are unchanged
open evidence gates. H0 parameter substitution does not establish bytecode equivalence.
All-output single-batch marketing is a substantive restriction: a producer or
intermediary able to split lots, retain stock, mix venues or respond to other traders
may behave differently. The next economic robustness gate should relax that restriction
before treating the lower-output mechanism as a general market-design prediction.
No new optimizer over beta or fee policy, no governance equilibrium, and no causal
environmental-effect estimate has been added in this gate.
