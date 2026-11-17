# Gate 21 — Smart-contract deposit-scale design with endogenous response

Date: 2026-11-17. Main topic: economic design of executable carbon-pool transaction
rules and contractual transmission. This gate makes the designer's decision
explicit; it does not claim an optimal revelation mechanism or governance equilibrium.

## 1. What smart contract does, and does not do

The source FeeCalculator at dynamic-fee-pools commit
7aef954dae1bd0c7add4ed66d216251110521b16 contains `setDepositFeeScale(int256)`
under owner control, with a permitted normalized range [0,1]. It uses project
inventory and transaction quantity to calculate dynamic fees and configured shares
to allocate tokens. Pool source executes the corresponding mint/transfer paths
and fee cap. Gate 18 records the separate pool-source pin and evidence layers.

The smart-contract lever here is a = depositFeeScale. The designer observes one
initial public state and selects a before producer quantity is chosen. Ratio r,
single-project fee, recipient weights and commercial beta are fixed. A commitment
for one modeled horizon is assumed; owner permissions do not establish immutable
commitment or distributed governance. The chosen menu values are source-permitted
parameter inputs, not EVM-verified policies on the historical deployment.

Beta is an OFF-CHAIN procurement/pass-through contract primitive. It is not the
recipient vector stored in FeeSetup and is not automatically paid by the calculator.
The oracle/registry linkage supporting eligible physical removal remains outside
the fee contract. Price, outside-sale access, verified yield and pre-production
capital remain modeled assumptions, not effects supplied for free by blockchain.

## 2. Normative designer problem

For each known state, apply the Gate 20 globally solved producer/routing response
y*(a),z*(a). A normative environmental-market designer maximizes modeled eta*y*,
subject to an inventory-concentration limit and minimum generic fee-token budget:

    maximize over a in approved menu: eta*y*(a)
    subject to H_after(z*(a)) <= H_bar,
               F_a(z*(a)) >= B.

No activity means fee zero. B>0 is a generic recipient budget, NOT producer income
or a public estimate of operator costs. H_bar is a stated policy preference,
not a carbon-integrity threshold or measured welfare weight. This objective is
not inferred to be the actual CHAR owner's private objective.

The implemented approved menu is {.01,.02,...,.30}, fixed before looking at results.
All are positive: source fee-zero guards make an unqualified zero-scale benchmark
inappropriate for an active fee module. Comparisons are REAL-FORMULA counterfactuals,
not claims that every small trade remains nonzero after integer arithmetic.

Experimental assumptions: two-project pool, Q=100,q in {10,50,70}; eta=P=1,
v=.55,b0=.50,beta=.25,c=.15,k=.01,g=.10, unbounded working capital;
H_bar=H_initial+.02; B=.5 CHAR. S0 fixes r=.99 and source default a=.18;
H0 parameter counterfactual fixes r=1.25 with checkpoint a=.15 as reference.
The latter is still not a deployed-source equivalence proof. Each initial state
is optimized separately; no unobserved history or state-contingent governance
mechanism is silently estimated. Beta=.25 avoids the beta=1 routing indifference.

## 3. How a lower scale changes production

On a fixed admissible multi-project state write F_a(z)=a*f(z), where f'>0 and
f''>0 by Gate 19. Let s=P-v. Gross monetization is s*z-P*a*f(z), strictly concave.
Before its derivative zero the marginal gain is positive; afterward it is nonpositive.
Hence the gross optimized gain under available supply can be represented as

    H(y;a)= integral from 0 to eta*y of [s-P*a*f'(u)]_+ du.

If a finite log boundary exists, the positive part is zero after the earlier
finite gross optimum; extend the integrand by zero beyond the log boundary.
If no positive marginal gain exists, H is identically zero. The representation
therefore also covers no-participation and finite-saturation cases.

For a_low<a_high, the integrand is weakly higher at a_low. Thus H is weakly higher
at every y, and its marginal gain in y is weakly higher. With fixed gas,
V(y;a)=max(0,H(y;a)-g). Almost everywhere,

    V_y(y;a)=1{H(y;a)>g} * eta*[s-P*a*f'(eta*y)]_+.

Both factors are nonnegative and weakly higher when a falls. Integrating these
derivative inequalities shows V(y;a_low)-V(y;a_high) is nondecreasing in y.
Kinks are handled by absolute continuity on bounded supply intervals.

Now consider the smallest maximizing quantities y_low,y_high. If y_low<y_high,
optimality at both policies implies the above difference at y_low is at least its
value at y_high. Increasing differences implies equality. The optimality inequalities
must then both be equalities, so y_low is ALSO an optimum at a_high, contradicting
y_high being its smallest optimum. Therefore

    a_low<a_high implies y*(a_low)>=y*(a_high)

under the declared smallest-optimum tie rule. Gate 20's outside-on-tie selection
is the smallest optimum because the active optimum is never below y_out.
This is a selected-output theorem, not a unique-global-equilibrium theorem.
The single-project special branch is unaffected by a and gives equality; the
experiment excludes that state because its initial HHI is already 1.

## 4. Exact inventory constraint

Let H be initial project-level HHI and z the gross deposit into the selected
project. For any valid project inventory vector,

    H_after(z)=[Q^2 H+2qz+z^2]/(Q+z)^2.

For H<=H_bar<1, H_after<=H_bar is equivalent to

    (1-H_bar)z^2+2(q-H_bar Q)z+Q^2(H-H_bar)<=0.

The constant is nonpositive and the leading coefficient positive. On z>=0 the
feasible interval is [0,z_cap], where

    z_cap = [H_bar Q-q
             +sqrt((q-H_bar Q)^2-(1-H_bar)Q^2(H-H_bar))]/(1-H_bar).

This condition is not assumed to be a project-specific physical carbon constraint.
For the two-project experiment H=(q/Q)^2+((Q-q)/Q)^2. The calculation concerns
gross underlying inventory, not net pool-token minting.

## 5. A concentration constraint can preclude production expansion

Suppose a selected Gate 20 optimum has y*>y_out. It must use the active branch.
If its pooling lot were saturated strictly below available supply, H'=0 there,
while U_out is strictly decreasing above y_out; reducing y would improve profit.
At the saturation junction H'=0 as well, giving the same contradiction. Therefore
strict expansion must occur on the unsaturated branch:

    z*(a)=eta*y*(a)>eta*y_out.

Consequently, if the inventory policy imposes z_cap<=eta*y_out, every feasible
policy has y*(a)=y_out by this implication and the Gate 20 output-floor theorem.
Fee-token income and producer contractual income can still change. This gives
another precise barrier to expansion, distinct from working capital or beta=0.

For q=50 in the experiment z_cap=25<eta*y_out=35; for q=70, z_cap is about
8.541020<35. Thus any feasible scale in those states cannot expand production,
even if it is profitable and the menu were enlarged. A no-feasible-menu outcome
is a separate statement: it does not prove there is no feasible parameter in [0,1].

## 6. Global finite-menu design result, and its limits

If the finite feasible menu is nonempty, it has a smallest feasible scale a_min.
By the monotonic response result, y*(a_min)>=y*(a) for every other feasible a.
Thus a_min is a global weak optimum WITHIN THE APPROVED MENU. Other scales can
tie on output plateaus. The implementation enumerates all candidates and lists
all numerical ties, rather than silently claiming a unique optimum.

Neither fee revenue a*f(z*(a)) nor the feasible-policy set is assumed monotone.
A higher scale changes the optimized lot and can eliminate participation. Therefore
one cannot identify feasibility by treating the fee budget as a monotone constraint.
All 30 scales are tested. If none meets the constraints, report no feasible approved
policy; producer outside output does not become zero as a result.

For a continuous policy interval, the same ordering gives an optimum at the lowest
feasible scale IF that minimum exists. Existence and behavior at activation
discontinuities need separate proof. This gate does not substitute finite enumeration
for a global optimum over all real scales, arbitrary fee functions or governance rules.

## 7. Relation to the topic

The contract-specific part is the mapping from an actual permitted on-chain
parameter to its state-dependent marginal fee, executable lot and inventory
consequence. Partial routing, nested choice and revenue-sharing transmission are
general economic principles used to prevent overclaiming. A conventional operator
could implement the same formula; no exclusivity or blockchain superiority follows.
The research contribution sought is the economic design and limits of programmable
rules in this asset setting, not a proof that conventional fee computation is impossible.
