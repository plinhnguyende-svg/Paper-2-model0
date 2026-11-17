# Gate 19 — Endogenous production and channel choice

Date: 2026-11-17. Extends Gate 18; source-real analytical model, not a deployed
transaction finding. Main model: one producer/intermediary contract, one project,
one all-output deposit batch, fixed initial inventory and exogenous CHAR price.
This is a globally solved production/channel decision, not a market-clearing
equilibrium, optimal contract or governance game.

## 1. Economic institution and timing

Before production, producer and intermediary commit to an enforceable procurement
contract with baseline payment b0 per verified credit and contractual pass-through
beta in [0,1] of the incremental NET cash surplus from pooling. Neither parameter
is inferred from on-chain recipient shares. Existing credit rights are assigned
so that the intermediary can market the newly issued credits. The modeled trader
and producer do not receive calculator fees directly.

Initial pool inventory q for the producer's project and total Q>0 are fixed.
The producer chooses y>=0, incurs C(y)=cy+ky^2/2, and generates x=eta*y verified
credits deterministically, eta>0. Feasible cash requires C(y)<=L, c>=0,k>0,L>=0;
L may be unbounded. Later receipts are not pledgeable for advance financing.
Intermediary observes the resulting lot x and chooses the better of selling ALL
credits outside at v per unit or depositing ALL into the pool at known price P>0.
No splitting, batching, warehousing, strategic order flow or endogenous prices.
The expected configuration is known and fixed for the horizon; all non-calculator
checks are assumed satisfied, with no seeding/cap truncation or exemptions.

One-to-one deposit accounting is inherited from the published pool source:
x underlying in; x-F(x) CHAR to intermediary; F(x) minted to fee recipients.
Successful gas g>0 is paid only when choosing the pool channel. Outside costs are
normalized into v; verification is assumed successful. No failed execution is
introduced in this deterministic gate, so no independent success-probability
parameter or maxFee shock is silently retained from the old uncertain extension.

Require 0<=b0<=v and sufficiently liquid, costless CHAR conversion at exogenous P.
This is a contract assumption, not observed producer prices or token liquidity.
Fixed net ancillary biochar proceeds are omitted; if material, add them to the
economic primitives and redo quantitative interpretations.

## 2. Endogenous premium and producer objective

For an executable x>0, pooling relative to outside sale generates total surplus

    S(y)=(P-v)*eta*y-P*F(eta*y)-g.

The intermediary chooses pooling iff S(y)>0, outside sale iff S(y)<0; at zero
surplus we select outside. If pooling is infeasible it must use outside.
Premium per CORC is now Delta(y)=max(0,S(y))/(eta*y), rather than a fixed number.
At y=0 there is no transaction, cash fee or division by zero.

The producer receives b0*eta*y+beta*max(0,S(y)), so its profit is

    U(y)=(eta*b0-c)*y-k*y^2/2+beta*max(0,S(y))

on valid pool states, and the outside-only expression otherwise.
This contains the feedback omitted by the fixed-premium closed form.

Intermediary outside margin is (v-b0)*x>=0. In a profitable pool state it is
(v-b0)*x+(1-beta)*S(y)>=0. Therefore the channel choice and promised producer
payment satisfy intermediary participation under the contract assumptions.
The entire surplus S is NOT itself an extra fee receipt or social benefit.

## 3. Deposit cost, derivatives and admissible domain

For q<Q and source-formula parameters a>0,r>0,

    F(x)=a[q log10(1-r*q/Q)
           -(q+x)log10(1-r*(q+x)/(Q+x))].

For q==Q the special branch is F(x)=d_single*x with 0<d_single<=1.
If r>1 and q<Q, the dynamic log domain requires

    0<x<(Q-r*q)/(r-1).

There is no positive dynamic action when q>=Q/r. This does not restrict the
q==Q special branch, and is not a universal concentration cap.
At r<=1 the dynamic domain has no finite upper bound (q<Q).
The calculator also needs 0<F(x)<=x. Whole-pool checks are separate.

Write h=Q-q>0,z=q+x,A=(1-r)*z+h,B=z+h. These are algebraic proof variables,
not additional economic primitives. On the log domain A>0,B>0:

    F'(x)=a/ln(10)*[-ln(A/B)+r*h*z/(A*B)],
    F''(x)=a*r*h^2*(A+B)/(ln(10)*A^2*B^2)>0.

Proof: F is a constant minus a*z*ln(A/B)/ln(10). Product/chain rules give
F'=a[-ln(A/B)-z((1-r)/A-1/B)]/ln(10).
Since A-(1-r)B=r*h, the second term is +r*h*z/(A*B).
Differentiating and collecting gives numerator
r*h[2AB-z((1-r)B+A)]=r*h^2[(2-r)z+2h]=r*h^2(A+B).
Every remaining factor is positive. For x>0, A/B<1 and z>0, hence F'>0.
At x=0 define the analytical extension F(0)=0; this is not a zero-fee transaction.

S0 uses a=.18,r=.99,d_single=.10. H0 parameter counterfactual uses a=.15,r=1.25
in the SAME source formula. It remains a counterfactual: historical source-bytecode
equivalence has not been established. Neither case emulates EVM quantization.

## 4. Global solution by two branches

Define the outside branch and the hypothetical pooling branch:

    U_out(y)=(eta*b0-c)y-k*y^2/2,
    U_pool(y)=U_out(y)+beta[(P-v)eta*y-P*F(eta*y)-g].

The realized objective is the larger branch at each feasible y. It need not be
concave even though each branch is strictly concave. The liquidity bound is

    y_L=(sqrt(c^2+2kL)-c)/k,

or infinity when L is unbounded. The outside optimum is

    y_out=min(y_L,max(0,(eta*b0-c)/k)).

For beta>0, on the dynamic pool branch,

    U_pool'(y)=eta*b0-c-k*y+beta*eta[P-v-P*F'(eta*y)],
    U_pool''(y)=-k-beta*P*eta^2*F''(eta*y)<0.

For the single-project linear fee the second derivative is -k<0 as well.
Thus there is at most one pool-branch stationary point. If the derivative at zero
is nonpositive, the branch maximum at its zero extension is -beta*g<0 and cannot
beat abstention. Otherwise find its unique derivative zero, unless an attainable
cash bound arrives first; in that case use that cash endpoint if the derivative
there remains nonnegative. Bisection suffices because the derivative strictly decreases.

Existence: if the r>1 log boundary is finite, F and F' diverge to positive infinity
as it is approached, hence U_pool tends to negative infinity. The maximizer is
therefore separated from that open boundary. With no finite boundary, the term
-k*y^2/2 and nonnegative F force U_pool to negative infinity as y grows.
With finite cash cap, compactness applies unless the excluded boundary is reached,
where the preceding divergence again gives an interior maximizer.

Compare the two branch maximum VALUES, not just their stationary points. Choose
the pool candidate only when it strictly exceeds the outside maximum; otherwise
choose outside. At exact equality both quantities are global solutions if distinct;
the declared tie convention selects outside. Numerical near-ties are labeled as
such and do not prove an exact mathematical equality.

### Why the fee<=x guard creates no missing profitable optimum here

We can first maximize U_pool over its log domain. If a positive-y candidate has
F(x)>=x, then S(y)<=(P-v)x-Px-g=-v*x-g<0, because v>=0 and g>0.
It is dominated at the SAME y by U_out, which is itself no larger than the global
outside maximum. Conversely, any strict improvement over the outside maximum
must have S>0 and 0<F<x. Hence relaxing this guard during the branch calculation
cannot create a falsely profitable global pool solution. This argument does NOT
justify ignoring arbitrary eligibility, cap, allowance or seeding constraints.

For beta=0, y_out is the unique production optimum. Intermediary may still pool
at that quantity if it has positive surplus and the calculator action is valid.
Thus zero upstream pass-through does not imply no market participation.

## 5. New economic result: higher profit need not mean higher production

Let S0(y)=(P-v)eta*y-P*F(eta*y), excluding fixed gas. Suppose beta>0, outside
output y_out is positive with slack cash and admissible pooling, and

    S0(y_out)>0,
    S0'(y_out)=eta[P-v-P*F'(eta*y_out)]<0.

At g=0, U_pool(y_out)>max U_out, while U_pool'(y_out)=beta*S0'(y_out)<0.
Strict concavity implies the unique pool optimum y_pool is less than y_out,
and its maximum still strictly exceeds the outside maximum. Changing g subtracts
the constant beta*g from the pool branch but leaves its maximizing quantity unchanged.
Therefore for all sufficiently small POSITIVE g, the global choice is pooling,
producer profit is higher, and physical output is lower than the outside-only optimum.
These are strict inequalities, so the phenomenon is not confined to a knife-edge tie.

The mechanism is diminishing incremental monetization surplus: average pooling
benefit remains positive, but its marginal benefit at the outside-optimal scale is
negative because inventory-dependent marginal fees are high. This result belongs
to the assumed all-output single-batch contract; splitting or dynamic inventory
adjustment could change it and has not been solved here.

### Two global maximizers can coexist

Under the preceding conditions let V_pool0=max U_pool with g=0 and V_out=max U_out.
Set g_critical=(V_pool0-V_out)/beta>0. At that exact gas cost the two distinct branch
maxima tie. Thus general uniqueness of the GLOBAL production choice is false,
although each branch has a unique optimum. Fee/rule discontinuity across inventory
states is not needed for this nonuniqueness: channel choice alone suffices.

### Conditional comparative static in beta

At a strictly interior, selected pool optimum, implicit differentiation yields

    dy_pool/dbeta
      =eta[P-v-P*F'(eta*y_pool)]/[k+beta*P*eta^2*F''(eta*y_pool)].

The denominator is positive and the numerator can have either sign. Maximized
producer profit is weakly increasing in beta because max(0,S(y))>=0 at every y;
there is no corresponding unconditional monotonic-output theorem. At channel or
cash switches, use global value comparisons and one-sided analyses instead.

## 6. Why the old frozen-premium output is not a universal bound

At a positive selected pool output let x=eta*y and Delta(y)=S(y)/x. Then

    Delta'(y)=eta[g-P(x*F'(x)-F(x))]/x^2.

This follows by differentiating (P-v)-P*F(x)/x-g/x. Convexity makes
x*F'-F positive, while fixed gas dilution contributes the opposite sign.
Consequently Delta can first increase and later decrease with quantity.

If one freezes the premium at THIS output and ignores cash/corner clipping, the
old stationary expression differs from the true endogenous stationary output by

    y_frozen-y = beta*eta/k*[P(F'(x)-F(x)/x)-g/x].

Its sign is not fixed. Arbitrary frozen quotes are even less directly comparable.
The CSV's frozen-at-outside-lot diagnostic is explicitly a counterfactual diagnostic,
not a new calibration or a general ranking of Gates 12 and 19.

## 7. Verification, interpretation and remaining limits

`scripts/gate19_endogenous.py` applies the analytic global reduction with 75-digit
Decimal calculations and 200 bisection steps. This is a numerical implementation
of a proven reduction, not formally directed interval arithmetic. A 1e-45 value-gap
tolerance flags numerical ties. Dense independent float searches and closed-form
single-project checks corroborate it; proofs establish the general results.

Scenario grid: 504 entirely synthetic configurations across source-default and
historical-parameter counterfactuals, seven inventory states, three outside values,
four beta values and three liquidity cases. It does not measure actual project output.
Full pool execution, historical transaction reconciliation and producer attribution
remain separate open evidence gates. No blockchain superiority, optimal beta,
endogenous token price or environmental additionality is established.
