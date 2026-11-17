# Gate 20 — Partial pooling and batch-splitting robustness

Date: 2026-11-17. Extends Gates 18–19 with fixed beta, initial inventory, prices,
eligibility and pre-production finance. No empirical producer attribution or
historical transaction proof is added. S0 is the pinned source real-formula model;
H0 parameter substitution is still a counterfactual, not a deployed oracle.

## 1. Change to the institution

Producer chooses y>=0 and creates x=eta*y eligible credits. The intermediary may
deposit any z in [0,x] into the pool and sell x-z outside at unchanged unit value v.
No minimum outside lot, outside capacity constraint, extra outside fixed charge,
mandatory all-output covenant or endogenous price is imposed. Pool gas g>0 is
paid only if a positive pool transaction is selected. Credit-rights and enforceable
cash pass-through assumptions remain exactly those in Gate 19.

Define gross incremental pooling gain before gas

    G(z)=(P-v)z-P F(z), G(0)=0.

The intermediary chooses the best feasible z, or does not pool. Define

    H(y)=max_{0<=z<=eta*y, pool domain} G(z),
    V(y)=max{0,H(y)-g}.

Producer profit is

    U_partial(y)=(eta*b0-c)y-k*y^2/2+beta*V(y),

with cy+ky^2/2<=L. The outside benchmark is unchanged. The baseline procurement
payment covers ALL eta*y credits, not only z. Total premium is based only on the
incremental surplus of the pooled portion; unused credits are not destroyed.

Intermediary margin is (v-b0)eta*y+(1-beta)V(y)>=0 when 0<=b0<=v.
At beta=0 the producer's output can remain unchanged while intermediary still pools.

## 2. Lot optimization for the source-real formula

Gate 19 proves F''(z)>0 on the dynamic log domain. Consequently

    G'(z)=P-v-P F'(z),
    G''(z)=-P F''(z)<0.

If G'(0)<=0, the best gross pooling gain is zero at z=0 and g>0 rules out pooling.
If G'(0)>0 and there is a finite derivative zero, let z_star be its unique solution.
If G' stays positive at every finite admissible z, set z_star=infinity as a notation
for no saturation at finite quantity, not an infinite executed trade.

The quantity-limited gross optimizer is

    z_hat(y)=min{eta*y,z_star},
    H(y)=G(z_hat(y)).

The actual choice is z_hat only if H(y)>g; otherwise it is zero (outside tie-break).
At a finite z_star, G' is zero and H smoothly becomes constant. Before saturation,
H'=eta G'(eta*y)>=0 and H''=eta^2 G''(eta*y)<0; after saturation H'=H''=0.
Thus H is nondecreasing and concave. In the single-project branch F(z)=d*z,
G is linear: use all available quantity if P-v-Pd>0, otherwise choose no pool.

For r<1, the limiting marginal fee is -a log10(1-r). If P-v is at least P times
that limit, no finite saturation occurs. For r>=1 and an admissible dynamic initial
state, F' diverges, so the positive-derivative case has a finite z_star.
For r>1 and q>=Q/r with q<Q, the dynamic action set is empty; the single-project
special branch remains separate.

The fee<=z guard does not exclude a strictly profitable gross optimizer: F>=z
implies G<=-v*z<=0, dominated by G(0)=0. Any selected pool trade satisfies
G>g>0 and therefore 0<F<z. Other execution constraints must still be assumed or
modeled explicitly. Integer/EVM discontinuities are not approximated by this solver.

## 3. Global production choice

Again use two branches:

    U_out(y)=(eta*b0-c)y-k*y^2/2,
    U_active(y)=U_out(y)+beta H(y)-beta*g.

Realized profit is max(U_out,U_active). Each branch is strictly concave (k>0),
although their maximum need not be concave at activation. The active derivative is

    eta*b0-c-k*y+beta H'(y),

which strictly decreases. Find its unique stationary point or cash endpoint, then
compare branch MAXIMUM VALUES. When eta*y_out>=z_star, both the base profit and
gross pooling gain are already maximized at y_out, so the active maximizer is
exactly y_out. Otherwise use the decreasing-derivative root and cash bound.
At equality of two distinct branch maxima, two global quantities may coexist;
the implementation selects the outside quantity and flags numerical near-ties.

The concavity/root reduction is for the source-real cost family. For arbitrary
counterfactual policies (e.g. clipping that changes curvature), it must be rechecked.

## 4. Main robustness theorem: partial pooling cannot lower baseline output

For y2>=y1 the feasible pooling quantities under y1 are still feasible under y2:
the intermediary can reuse the old lot z and sell the extra credits outside.
Therefore H and V are nondecreasing. This nested-choice argument does NOT require
convex fees, smoothness or a positive pooling probability.

Let y_out be the unique outside-only optimum on the cash-feasible interval.
For any y<y_out, strict concavity of U_out gives U_out(y)<U_out(y_out), and
nondecreasing V gives V(y)<=V(y_out). With beta>=0,

    U_out(y)+beta V(y) < U_out(y_out)+beta V(y_out).

Thus no y<y_out is a global optimum:

    every optimal y_partial >= y_out.

This is a structural theorem, not merely an absence of negative cases in a grid.
It relies on free partial venue allocation, unchanged outside sales terms and a
fixed cash-feasible set. If ownership/covenants force all-output pooling, outside
capacity is limited, selling the remainder costs extra, or prices respond to total
output, the proof's nested-choice step may fail. The theorem is not uniquely
blockchain-specific; its role is to identify which economic restrictions drive
transmission in this smart-contract application.

## 5. Consequence for the Gate 19 negative-output result

Every all-output action remains available under partial allocation: z=eta*y.
Hence V_partial(y)>=V_all_output(y) pointwise and

    maximum producer profit under partial allocation
       >= maximum producer profit under all-output restriction.

The six negative-output grid cases from Gate 19 cannot remain negative relative to
the outside benchmark under Gate 20 assumptions. The old result is mathematically
valid for its restriction, but is NOT robust to this extension. It must not be
promoted as a general theorem that smart-contract pooling reduces physical supply.
Nor does the new result establish strictly more supply: equality is possible.

## 6. Pass-through, saturation and cash

At a selected, positive, unsaturated interior active optimum,

    dy/dbeta = H'(y)/[k-beta H''(y)] >= 0.

The denominator is positive. At saturation H'=0, so there is no marginal production
effect. If y_out already supplies z_star, the producer can receive additional
contractual income from pooling while output stays at y_out.

Global monotonicity follows as well. For beta2>beta1, suppose respective optima
y2<y1. Optimality at both beta values implies

    (beta2-beta1)[V(y1)-V(y2)] <= 0.

Because V is nondecreasing, its difference must be zero. The two optimality
inequalities then require U_out(y1)=U_out(y2). But both outputs are at least y_out,
where U_out is strictly decreasing away from its unique maximum, so equality at
distinct quantities is impossible. Thus production cannot fall as beta rises
while all other primitives and feasible sets remain fixed. At the same beta,
multiple maximizing quantities may still tie.

Beta=0 yields the outside production optimum. If the outside optimum already equals
the cash bound, production remains at that bound for all beta: partial pooling
does not itself supply pre-production finance. A plateau in output can also arise
from monetization saturation, even when working capital is abundant.

## 7. Same-project self-batching does not reduce ideal total fees

Let F(q,Q,z)=a[A(q,Q)-A(q+z,Q+z)] with

    A(q,Q)=q log10(1-r*q/Q).

For consecutive self-batches z1,...,zn into the same project, before batch k the
state is q+sum_{i<k}zi,Q+sum_{i<k}zi. Summing the potential differences telescopes:

    sum_k F(q+sum_{i<k}zi,Q+sum_{i<k}zi,zk)
      = F(q,Q,sum_k zk).

In the exact single-project branch the same identity follows from linear fees.
There are no intervening trades, parameter changes, exemptions, seeding/cap
transitions or other projects introduced. With gas g per call, n successful
batches have the same gross real fee and (n-1)g more cost than one batch.
Thus self-splitting is weakly dominated (strictly for n>1,g>0) when both paths
are executable. If every split quote is valid, the telescoping total is positive
and no more than total quantity, and the final log-domain condition also makes
the unsplit quote valid in this ideal family.

This is NOT an EVM fee-conservation or no-exploit theorem. Fixed-point log rounding,
recipient rounding, zero-fee guards, third-party interleaving, fee changes and actual
pool thresholds can destroy the identity. Separate deployed execution tests are
required before making a claim about batching on mainnet.

## 8. What is now established

Partial pooling removes the earlier lower-output counterexample under stated
conditions; greater producer income need not mean greater output; finite optimal
pool lots can saturate transmission; and ideal same-project batching does not
improve it after gas. Actual producer cash receipts and additional removal remain
unverified. This gate does not optimize governance, beta or the full fee-rule space.
