# Gate 18 — Consolidation and revalidation result

Date: 2026-11-17. Formal/implementation consolidation is complete within the scopes
below; full deployed-transaction verification and a closed endogenous supply-chain equilibrium remain open.

## Deliverables

- [Master specification](GATE18_MASTER_SPECIFICATION.md): agents, timing, units,
  accounting, outside options, uncertainty, choice rights and producer assumptions.
- [Re-derived proofs](GATE18_PROOFS.md): eleven groups of propositions, with domain,
  existence, corner and identification qualifications.
- [Claim audit](GATE18_CLAIM_AUDIT.json): 23 claims classified by evidence and scope.
- [Benchmarks](../config/benchmarks.json): pinned source defaults separated from
  observed historical parameters and participant-attribution gaps.
- `scripts/gate18_model.py`, `tests/test_gate18.py`: deterministic analytical
  evaluation, fee accounting, producer response and finite policy enumeration.

## Material qualifications and clarifications

1. Fee-recipient identity matters for participation (already recognized in the recovered
   Gates 9–10 originals; retained explicitly here): a trader receiving its own fee
   has a different net payoff. Otherwise changing only recipient weights cannot
   affect disjoint traders with exogenous prices and unchanged contracts.
2. Redemption net receipts can be less than calculator shares because of configured
   burn-address transfers and integer rounding. Gross allocation is not net income.
3. The maxFee threshold need not be unique and is conditional on an admissible cap;
   submission must be compared with abstention. The pool can require a positive cap.
4. A fixed source-default boundary extension cannot be transported to ratio 1.25.
   A domain exclusion is not a universal 80% pool-concentration cap.
5. The producer fee derivative needs positive output as well as slack liquidity and
   a positive premium. The recovered Gate 12 appendix ALREADY states these conditions
   and includes the success-probability factor. Its simplified summary omitted detail;
   this is a consolidation qualification, not a newly found error in that proposition.
6. The producer closed form requires a fixed unit premium. If own output changes
   the marketed lot and therefore the inventory-dependent premium, re-solve the
   nonlinear producer problem. A closed supply-chain equilibrium is not established.
7. Real-formula, source EVM, deployed calculator and full-pool transaction evidence
   are separate. The observed-parameter/source-formula combination is a counterfactual.

## New finite computational experiment

36 independent synthetic one-depositor scenarios: inventories (50,50), (99,1),
(100,0); owned project 0/1; outside values .55/.85/.98; success gas .01/.10.
P=1. Quantities: abstain, .25,1,2,5,10. Each actor owns enough of its specified
project outside the pool to choose any declared amount, including when pool inventory
for that project is zero. No claim that all states occur on mainnet.

Seven policies: five flat rates, source-default ideal formula, and source formula
with historical deposit parameters. Objective: total chosen volume. Constraints:
per-scenario HHI no more than source baseline +.02 and aggregate fees at least 70%
of source baseline. All parameters and constraints are assumed, not calibrated.

| Policy | Volume | Feasible under declared constraints |
|---|---:|---|
| Flat 1% | 300 | No |
| Flat 5% | 240 | No |
| Flat 10% | 240 | No |
| Flat 20% | 120 | No |
| Flat 35% | 120 | No |
| Source-default real formula | 260 | Yes |
| Historical-parameter counterfactual | 240 | Yes |

Source-default is the highest-volume feasible candidate in THIS experiment. This
does not establish its real-world optimality, nor an intrinsic benefit of dynamic
fees. It shows why constrained volume and unconstrained volume cannot be conflated.
The largest unrestricted volume (flat 1%) violates the stated constraints.
There is no improvement claim for a proposed alternative policy.

Reproduce from repository root:

```sh
python3 -m unittest discover -s tests -p 'test_gate18.py' -v
python3 scripts/gate18_model.py --out results/gate18
```

Eight local tests passed, including atom/gap cap nonuniqueness, integer conservation,
strict domain boundary, self-recipient participation reversal, producer corners,
and an independent HHI identity. These checks support the implementations; the
analytic proofs carry the general statements. CI results are separate evidence.

## Transaction reconciliation workstream

Gate 17 collector remains read-only, fail-closed on incomplete scans, and archived
by the existing Foundry workflow. Its latest previously inspected run 44002883696
failed eth_getLogs with HTTP 429 / request limit reached. No successful live
collection or fee matching is inferred from the new economic tests.
The next CI run retries this inherited collection workstream independently of the
new offline economic job. If still blocked, the result stays OPEN.

Acceptance requires canonical receipt identity, actual deposit/redemption decoding,
exact intra-block prestate, active-module linkage, fee reproduction, underlying
movement, net recipient plus burn-address transfers, and project mapping. The
fee recipient to producer mapping remains a separate attribution requirement.

## Gate verdict

| Component | Verdict |
|---|---|
| Consolidated analytical specification | COMPLETE with explicit baseline assumptions |
| Re-derived scoped propositions | COMPLETE as stated in GATE18_PROOFS.md |
| Original Gates 9–13 main numerical workflows | REPLAYED; 27 regenerated CSVs agree within 1e-10 |
| Benchmark separation | COMPLETE; bytecode equivalence still OPEN |
| Participant response + designer | COMPLETE for declared finite deterministic model |
| Functional optimality / strategic equilibrium | NOT CLAIMED |
| Producer transmission | CONDITIONAL fixed-premium extension |
| Actual transactions / producer attribution | OPEN |

Next gate should test the most economically consequential remaining extension:
endogenize marketed lot x=eta y and unit premium, or strategically model rule
commitment, choosing one rather than adding both at once. The recovered original appendices remain scoped real-formula and hypothetical
contract results; numerical reproducibility does not upgrade their empirical status.

## Original workflow replay, additional to the new seven-policy experiment

Original Gate 9: seven unit tests pass; full 160-replication policy run, 40,000
execution stress cases and 110 joint replications replay successfully.
Original Gate 10: full default 100-replication/180-round run and internal checks pass.
Original Gate 11: 14 policies x 4 buffers x 3 scenarios x 40 replications = 6,720
simulation replications. Twelve of 40 continuity/monotonicity-eligible candidates
meet constraints; the original three extension policies at buffer .30 remain tied.
Original Gate 12: internal checks, 16 baseline scenarios and 320 sensitivities replay.
Original Gate 13: five built-in identification/feasibility checks and 20 cases replay.

27 actually regenerated archived CSVs (not untouched snapshot inputs) agree at
rtol=atol=1e-10, with matching schemas/row counts and text columns. Independent
replay copies preserve the original archives. A few generated ancillary outputs
are outside the archived-CSV comparison and are not silently counted as matches.

Gate 11 paired holdout volume differences: single-project +16.0679 with 95% Monte
Carlo t interval [-34.9861,67.1219]; near-monopoly +17.5887 with interval
[-17.2506,52.4280]. Both include zero. These are simulation intervals, not causal
confidence intervals for actual CHAR outcomes. The new seven-policy static experiment
uses different assumptions and constraints: its ranking does not contradict or
replace the original dynamic-arrival experiment.

Original Gate 10 already considers trader self-recapture and positive-cap constraints.
Original Gate 12 already imposes positive interior output and fixed success
probability pi, yielding dy*/dd=-eta beta pi P/k, with pi=1 in its baseline.
These should be preserved rather than misreported as newly discovered flaws.

The main genuinely unresolved economic linkage is whether the producer is small
enough to take the per-unit monetization premium as fixed; if not, Delta(y) must
be endogenized before a unified production-market equilibrium can be claimed.
