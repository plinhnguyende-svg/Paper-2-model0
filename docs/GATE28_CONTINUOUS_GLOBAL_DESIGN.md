# Gate 28 — Continuous Global Fee Design: Proofs, Regimes, and Numerical Scope

**Date:** 17 November 2026. **Research branch:** research/char-evm-verification-pr, draft PR #21 into research/char-refi-standalone; do not merge into legacy main.

**Evidence:** [Gate 28 workflow](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/workflows/char-gate28-continuous-design.yml), [solver](../scripts/gate28_continuous_global.py), [unit tests](../tests/test_gate28_continuous_global.py). The deployed contracts were independently verified in Gates 25–27, but the economics below is a **real-arithmetic model under hypothetical contract and price assumptions**, not EVM-calibrated behavior or measured carbon removal.

## 1. Agents, decisions and sequence

The designer observes initial project inventory \(q\) and total pool inventory \(Q>q\), fixes ratio \(r>0\) and other terms, and chooses **one continuous fee scale \(a\in(0,1]\)** for the model horizon. The producer chooses physical output \(y\ge0\), yields \(\eta y\) eligible credits, incurs cost \(cy+ky^2/2\), and is bound by early liquidity \(cy+ky^2/2\le L\). The intermediary purchases the credits under an assumed enforceable procurement contract and may pool any \(z\in[0,\eta y]\), selling the remainder externally at value \(v\). If pooling is selected, it costs fixed gas \(g>0\). Only a contractual fraction \(\beta\in[0,1]\) of *incremental net pooling surplus* passes upstream.

The modeling restrictions are \(Q>q\ge0\), \(P>v\ge b_0\ge0\), \(\eta,k>0\), \(c,g\ge0\) with \(g>0\); fixed \(P,v,b_0,\eta,c,k,\beta,r,L,g\) over the horizon. **Producer income, intermediary sales proceeds and protocol fee recipients are distinct entities.** Beta is not a protocol share, has not been measured, and does not represent preproduction finance.

The dynamic deposit fee is \(F_a(z)=a f(z)\), where

\[
f(z)=q\log_{10}\left(1-r\frac qQ\right)
 -(q+z)\log_{10}\left(1-r\frac{q+z}{Q+z}\right),\qquad f(0)=0.
\]

On the admitted log domain, \(f'(z)>0\) and \(f''(z)>0\). The source has a separate single-project special branch when \(q=Q\); this Gate deliberately excludes it from the dynamic-scale designer problem. This is a model in real numbers, not fixed-point EVM rounding.

## 2. Full operational equilibrium, not an FOC-only solution

At chosen fee scale \(a\), define gross intermediary incremental gain

\[
G_a(z)=(P-v)z-Pa f(z).
\]

This is strictly concave in eligible pooled quantity \(z\). At each \(y\), the best gross lot is \(\widehat z(a,y)=\operatorname*{argmax}_{0\le z\le\eta y}G_a(z)\) on the admitted dynamic domain. The intermediary pools only if \(G_a(\widehat z)>g\), and chooses outside at equality. The producer maximizes

\[
U_a(y)=(\eta b_0-c)y-\frac k2y^2+
 \beta\max\{0,G_a(\widehat z(a,y))-g\}
\]

subject to early cash and fee-domain constraints. Gate 20 solves this **globally** by comparing the maximum value of the outside strictly concave branch and the maximum value of the active strictly concave branch. The output floor is \(y^*(a)\ge y_0\), where

\[
y_0=\min\left\{y_L,\max\left(0,\frac{\eta b_0-c}{k}\right)\right\},
\quad y_L=\frac{\sqrt{c^2+2kL}-c}{k}
\]

for finite \(L\); take \(y_L=\infty\) for no early cash bound.

The solver separately labels and checks these regimes:

- **Outside/nonparticipation.** No profitable pool option after gas or no active producer value advantage. Recipient fee budget is zero.
- **Active unsaturated supply binding.** \(z=\eta y<z_\star(a)\), with positive marginal gross return; at a cash-slack interior producer optimum,
\[
\eta b_0-c-ky+\beta\eta[P-v-Pa f'(\eta y)]=0.
\]
- **Active saturated lot.** \(z=z_\star(a)<\eta y\), where \(P-v=Pa f'(z_\star)\). If \(z_\star(a)\le\eta y_0\), equilibrium output is \(y^*=y_0\), even if intermediary income and contractual transfer are positive.
- **Active early-liquidity binding.** Output reaches \(y_L\), and altered downstream trading or settlement does not itself relax the early-funding constraint. If \(y_0=y_L\), supply cannot expand.
- **Contract pass-through endpoints.** At \(\beta=0\) the producer's equilibrium output equals \(y_0\), although intermediary trading may remain positive. At \(\beta=1\), surplus-maximizing routing must be contractually specified or chosen by an explicit producer-favoring tie-break; intermediary routing incentives are otherwise weak.

These cases and activation boundaries are addressed by the underlying global value comparison. The active FOC alone is not an equilibrium certificate.

## 3. Proposition: scale ordering of output and actual pooling

For \(a_1<a_2\), the Gate 21 increasing-differences proof gives \(y^*(a_1)\ge y^*(a_2)\) for the declared outside-on-tie selection. At a given available lot, \(G_a'(z)=P-v-Paf'(z)\) is weakly larger at smaller \(a\). Its unique gross-maximizing lot \(z_\star(a)\) is therefore nonincreasing in \(a\). The quantity cap \(\eta y^*(a)\) is also nonincreasing in \(a\). Consequently the selected actual pooled lot, equal to the smaller of the gross-optimal lot and available supply when pooling is active, is weakly nonincreasing in \(a\).

Activation cannot reverse this ordering: lower fees weakly increase the best active return at every output and cannot eliminate a previously strictly profitable active opportunity. Thus

\[
a_1<a_2 \Longrightarrow
 y^*(a_1)\ge y^*(a_2),\qquad z^*(a_1)\ge z^*(a_2).
\]

These are output/routing comparisons **at fixed prices, one state and one horizon**, not dynamic cross-block strategic trading results.

## 4. Exact inventory-composition constraint

For two projects and a gross underlying deposit \(z\),

\[
H_0=\frac{q^2+(Q-q)^2}{Q^2},\qquad
H(z)=\frac{(q+z)^2+(Q-q)^2}{(Q+z)^2}.
\]

If \(H_0\le\bar H<1\), \(H(z)\le\bar H\) is equivalent to

\[
(1-\bar H)z^2+2(q-\bar H Q)z+Q^2(H_0-\bar H)\le0,
\]

so the complete feasible gross-lot interval is \(0\le z\le z_{\max}\), where

\[
z_{\max}=
\frac{\bar H Q-q+
\sqrt{(q-\bar H Q)^2-(1-\bar H)Q^2(H_0-\bar H)}}
{1-\bar H}.
\]

This is not an estimated carbon-integrity constraint, and is based on underlying inventory, not pool-token mint amounts.

## 5. Theorem 28.1: global weakly optimal continuous fee scale

The one-state designer chooses \(a\) over **the entire** \((0,1]\), maximizing modeled \(\eta y^*(a)\), subject to

\[
a f(z^*(a))\ge B>0,\qquad z^*(a)\le z_{\max},
\]

as well as all underlying contract and execution requirements.

**Theorem.** If the set of feasible fee scales has a smallest member \(a_{\min}\), that fee scale maximizes \(\eta y^*(a)\) over *all* feasible continuous scales. This optimum need not be unique.

**Proof.** Every feasible \(a\) satisfies \(a\ge a_{\min}\), so the just-proved output ordering yields \(y^*(a)\le y^*(a_{\min})\). Multiplication by \(\eta>0\) gives the result. Participation switches, gas and budget constraints affect the feasible set but do not invalidate the ranking of its members. Existence of a least feasible member must still be checked or imposed as an explicit condition, rather than assumed from the old finite menu.

Fee revenue \(R(a)=a f(z^*(a))\) is **not assumed monotone**, because the direct rise in \(a\) is opposed by a decrease in \(z^*(a)\). A naive bisection of \(R(a)=B\) over \((0,1]\) therefore does not give a global certificate.

## 6. Whole-domain monotone exclusion algorithm

For any scale interval \(0<\ell\le a\le u\le1\), the output-and-lot monotonicity implies

\[
z^*(u)\le z^*(a)\le z^*(\ell),\qquad
R(a)=a f(z^*(a))\le u f(z^*(\ell)).
\]

Thus the entire interval is infeasible if either \(z^*(u)>z_{\max}\) or \(u f(z^*(\ell))<B\). Neither exclusion requires fee revenue to be monotone.

The code also covers \(\ell=0\) without evaluating a forbidden zero-fee transaction: a universal bound on producer output is

\[
y^*(a)\le \min\left\{y_L,
\max\left[0,\frac{\eta b_0-c+\beta\eta(P-v)}{k}\right]\right\}.
\]

The derivative of the pooling premium never exceeds \(\eta(P-v)\), giving this upper bound. It yields a near-zero lot upper bound whenever the resulting quantity is inside the logarithm domain. If the domain does not allow that bound, the algorithm does **not** exclude the interval on that basis.

The search partitions the complete continuous scale domain, processes intervals from low to high scale, excludes them only using these necessary bounds, and retains the first unresolved narrow interval as a lower bound for the minimum scale. Each feasible upper endpoint is verified using the independently implemented Gate 20 global producer/routing solver, plus the exact two-project HHI and positive token-budget inequalities.

**Computational qualification:** 70-digit Python Decimal and numerical root bisection are not outward-rounded interval arithmetic. The displayed brackets are full-domain, proof-based *numerical* enclosures to the declared fee-scale tolerance, not a formal interval-arithmetic theorem certificate.

## 7. Theorem 28.2: global participation-versus-HHI impossibility

Assume \(z_{\max}<\eta y_0\), \(P>v\), and that \(z_{\max}\) lies within the smooth dynamic-fee domain. Define

\[
a_c=\frac{P-v}{P f'(z_{\max})}.
\]

**Theorem.** If \(a_c>1\), or if \(0<a_c\le1\) and

\[
(P-v)z_{\max}-P a_c f(z_{\max})\le g,
\]

then **no** fee scale in \((0,1]\) can simultaneously satisfy the HHI policy and positive token-fee budget \(B>0\).

**Proof, low fee scales.** For \(a<a_c\), the gross pooling marginal gain at the allowed lot cap is
\(G_a'(z_{\max})=P-v-Paf'(z_{\max})>0\). Strict concavity implies the unconstrained intermediary lot optimum is larger than \(z_{\max}\). The Gate 20 output floor \(y^*(a)\ge y_0\) ensures at least \(\eta y_0>z_{\max}\) credits are available. Therefore, whenever active pooling occurs, its optimal lot exceeds \(z_{\max}\) and violates HHI; otherwise its fee budget is zero.

**Proof, high fee scales.** For \(a\ge a_c\) and all admissible \(z\), \(G_a(z)\le G_{a_c}(z)\) because \(f(z)\ge0\). Strict concavity and \(G_{a_c}'(z_{\max})=0\) show \(G_{a_c}(z)\le G_{a_c}(z_{\max})\). If the latter is at most \(g\), no positive pool lot covers fixed gas. The outside tie-break then makes recipient fees zero. If \(a_c>1\), the first case alone covers all admissible fee scales. The proof covers all \(a\), not a selected numerical grid.

**S0 q=70 application:** With \(Q=100,q=70,r=0.99,\bar H=0.60,P=1,v=0.55,g=0.10,y_0=35\), the allowed lot cap is \(z_{\max}\approx8.5410196625<35\), critical scale \(a_c\approx0.52914564165\), and gross gain after gas at that critical scale is approximately \(-0.00351510938<0\). Hence **global infeasibility** holds for all positive token budgets under the stated model assumptions.

## 8. Six complete-domain numerical design results

All results are **synthetic**, with \(Q=100,\eta=P=1,v=0.55,b_0=0.50,c=0.15,k=0.01,\beta=0.25,g=0.10\), no early liquidity cap, budget \(B=0.5\), and HHI ceiling \(H_0+0.02\). S0 uses ratio \(r=0.99\) and baseline scale 0.18; H0 uses historical ratio \(r=1.25\) and baseline scale 0.15, while allowing the designer to vary the scale counterfactually. Neither benchmark measures real producer behavior.

| Benchmark | Project inventory q | Minimum feasible scale (numerical bracket) | Best tested feasible scale | Equilibrium modeled output | Earlier 30-scale menu |
|---|---:|---|---:|---:|---|
| S0 | 10 | [0.0450424194, 0.0450431824] | 0.0450431824 | 45.832764 | 0.05 |
| S0 | 50 | [0.6969905853, 0.6969912529] | 0.6969912529 | 35 | None |
| S0 | 70 | **Globally infeasible by Theorem 28.2** | — | Outside production 35 remains | None |
| H0 | 10 | [0.0328936768, 0.0328942871] | 0.0328942871 | 45.815257 | 0.04 |
| H0 | 50 | [0.4006361771, 0.4006369591] | 0.4006369591 | 35 | None |
| H0 | 70 | [0.2086197281, 0.2086205292] | 0.2086205292 | 35 | 0.21 |

The five numerical brackets have width **below \(10^{-6}\) fee-scale units**. They exploit *whole-domain* monotone exclusions but are not a formal machine-checked global optimum over arbitrary fee functions or integer-rounded execution.

The results reveal three economically different cases:

1. **Strict production expansion (q=10):** A lower continuous fee scale than the old discrete menu slightly increases modeled output while satisfying the fee-token budget. In this region the pooling choice remains unsaturated.
2. **Feasible fee-token collection without more production (q=50; H0 q=70):** Composition policy forces a small saturated lot, leaving optimal producer production at the outside benchmark 35. Two q=50 policies were missed entirely by Gate 21 only because its *approved menu ended at 0.30*.
3. **Structural infeasibility (S0 q=70):** The HHI cap requires a scale too high for intermediary participation, so no policy can generate a positive fee budget within the assumptions.

## 9. Early-liquidity, beta and gas robustness

The code additionally archives **three named synthetic robustness configurations** under the same historical-parameter ratio:

- Early liquidity \(L=5\) at q=10: the production cap binds. A positive pooling benefit cannot serve as cash that arrives before recovery begins.
- Contractual pass-through \(\beta=0\) at q=10: the producer output remains at its outside optimum even if the intermediary joins the pool.
- Prohibitive fixed gas \(g=50\): lack of intermediary participation defeats any strictly positive recipient fee budget.

The full report includes the numerical global-search status for these cases in REGIME_ROBUSTNESS_SYNTHETIC.json. Separately, tests verify outside, unsaturated, saturated and early-liquidity-binding responses. No environmental claim or real producer payment is inferred.

## 10. Gate decision and research boundaries

**Mathematics:** The one-dimensional *global policy-design characterization* and the structural no-feasibility theorem are analytic results, conditional on the Gate 20 equilibrium assumptions. The positive cases have continuous, full-domain numerical brackets; formal directed-rounding computer proof or exact closed-form optimal scale remains OPEN.

**Institutional interpretation:** This optimizes the economics of a smart-contract-executable fee rule, **not** blockchain technology against a conventional intermediary. The same functional policy can in principle be offered by a capable centralized platform; governance, commitment, credible settlement and multi-party rights remain distinct institutional questions. Protocol fee receipts do not identify \(\beta\), producer financing or actual incremental CDR.

**Next scientific priorities:** prove an economically specified commitment/governance mechanism against a capable conventional benchmark, or develop sensitivity/robustness to actual timing and integer rounding, without introducing unrelated hidden types or oracle errors. Preserve PR #21 as Draft and do not merge into legacy main.
