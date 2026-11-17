# Gate 18 — Re-derived propositions and their scope

All statements below use the master specification. They are new re-derivations of
the reported claims, cross-checks against the recovered original appendices. Their numerical workflows
were also replayed; this is not an assertion that every ancillary statement was formally verified.

## P1. Participation and fee ownership (economic assumptions)

For x>0, P>0 and disjoint trader/recipients, a feasible deposit weakly dominates
the outside option exactly when P(x-F)-vx-g_s >= 0. Dividing by Px>0 gives

    F/x <= 1-v/P-g_s/(Px).

For redemption, ux-P(x+F)-g_s >= 0 gives

    F/x <= u/P-1-g_s/(Px).

These are necessary and sufficient for a specified feasible lot, not existence
or uniqueness of the optimal lot. With deposit fee share a accruing to the trader,
net token receipt is x-F+aF, so the left side becomes (1-a)F/x.
If a=1, the fee is not a net private loss to that trader. Code labels cannot replace
beneficial-ownership evidence. Redemption must use net fee receipt after burn.

## P2. Optimal acceptance cap, and why uniqueness is not guaranteed

Assume fixed lot x, price P>0, fee F>=0 with fixed distribution, no self-rebate,
constant success gas g_s and failure gas g_f. Assume all other execution checks
pass in the states considered (or cap-independent failures add a constant term).
Gross surplus before fee/gas is
G=Px-vx for deposit, or G=ux-Px for redemption. A submitted transaction has

    U(m)=E[(G-PF-g_s)1{F<=m} - g_f 1{F>m}]
        =-g_f + E[(G-PF-g_s+g_f)1{F<=m}].

For m2>m1, subtraction yields

    U(m2)-U(m1)
      = E[(G-PF-g_s+g_f)1{m1<F<=m2}].

The integrand is positive for F<(G-g_s+g_f)/P, negative above, and zero at equality.
Thus a cap accepting all fee states below this threshold and rejecting all above
maximizes conditional utility whenever this acceptance set is representable by an
admissible cap. The deposit expression is

    m_D = x(1-v/P)-(g_s-g_f)/P,

and the redemption expression is

    m_R = x(u/P-1)-(g_s-g_f)/P.

No density assumption was needed. An atom exactly at the threshold has zero marginal
gain and can be accepted or rejected. Gaps in support imply many numerical caps
implement the same acceptance set. Therefore a unique optimal cap is NOT established.
If the threshold is below zero, all executable nonnegative fees are unattractive
conditional on submission; abstention with zero payoff dominates a sure failure
when g_f>0. If it is zero and cap must be positive, accepting a small positive-fee
atom may be unavoidable: do not assume a clipped-zero cap is a valid contract input.
For discrete integer caps, enumerate admissible caps/support thresholds and compare
the maximum to zero before submitting. For a finite fee support, nonempty acceptance
sets change only at support points; an empty set needs a separately admissible cap.
State-dependent gas, cap-dependent ordering and price impact invalidate this proof's
simple constant threshold and require a new model.

## P3. Inventory accounting (real numbers)

Let H=sum_j q_j^2/Q^2 and deposit x>0 into project j. The numerator after deposit is
sum q_k^2+2q_j x+x^2=Q^2 H+2q_j x+x^2; the denominator is (Q+x)^2. Hence

    H_after-H
      = [Q^2 H+2q_j x+x^2-H(Q^2+2Qx+x^2)]/(Q+x)^2
      = [2Qx(q_j/Q-H)+x^2(1-H)]/(Q+x)^2.

Since Q,x>0, concentration increases iff

    q_j/Q > H-x(1-H)/(2Q).

This is an accounting result for an exogenously selected deposit, not evidence
that the fee mechanism changes behavior. Inventory uses gross underlying x.

## P4. Real-formula boundary and dynamic-deposit domain

Use source-default positive deposit scale a and ratio r<1. For project inventory q,
total Q and deposit x, with q<Q, the ideal formula is

    D=a[q log10(1-rq/Q)-(q+x)log10(1-r(q+x)/(Q+x))].

For fixed q,x>0, set Q=q+epsilon and let epsilon decrease to zero. Both logarithm
arguments converge to 1-r>0, so continuity of log gives

    limit D = -a x log10(1-r).

At a=.18,r=.99 this is .36x. The special current==total branch instead gives .10x.
This proves a real-formula discontinuity. It is not an EVM epsilon-limit theorem.

For redemption 0<x<q, let b=.10 and c=.30. The ideal formula is

    R=c[(q-x)log10((q-x)/(Q-x)+b)-q log10(q/Q+b)
         +x log10(1+b)].

At Q decreasing to q, both ratios tend to 1. The expression becomes
c[(q-x)-q+x]log10(1+b)=0. At the exact single-project branch R=.10x.
The integer implementation's sign check, zero-fee guard and dust fallback can produce
different results at small finite epsilon. In particular the real limit does NOT
re-certify the old idealized near-zero redemption figures as EVM behavior.

For ratio r=1.25 and a dynamic deposit, the real domain requires

    1.25(q+x)/(Q+x)<1,
    1.25q+1.25x<Q+x,
    x<4Q-5q.

If q>=.8Q there is no positive admissible dynamic deposit. If q==Q, this reasoning
does not apply because the special branch bypasses it. Near q=Q with r>1, the
dynamic domain has no such admissible positive-x neighborhood. Reusing the .36x
extension in that benchmark is therefore invalid. Rounding can shift the exact
integer threshold; the real domain is not the complete pool execution condition.

## P5. Interior monotonicity and qualified clipping/extension

Fix Q,x and use the real, multi-project domain with valid positive logarithm arguments.
For deposit define t0=q/Q and t1=(q+x)/(Q+x). Since q<Q and x>0, t1>t0.
Differentiating gives

    dD/dq = a/ln(10) [h(t0)-h(t1)],
    h(t)=ln(1-rt)-rt/(1-rt).

For r>0, h'(t)=-r/(1-rt)-r/(1-rt)^2<0. Thus dD/dq>0.

For redemption with 0<x<=q<Q, t0=q/Q and t1=(q-x)/(Q-x) satisfy t1<t0.
Differentiating gives

    dR/dq = c/ln(10)[k(t1)-k(t0)],
    k(t)=ln(t+b)+t/(t+b).

For b>0, k'(t)=1/(t+b)+b/(t+b)^2>0. Thus dR/dq<0.
The conclusion concerns the raw real formula, not EVM truncation, zero-fee reverts,
fee>amount reverts or arbitrary inventory trajectories with Q changing.

Under source defaults, replace D by min(D,c0 x), where 0<c0<=.36,
and R by max(R,c0 x), and define both endpoint fees to be c0 x.
The limits in P4 imply continuity at q=Q, and monotonicity is weakly preserved by
min/max with a constant. The extension rule defining D(Q,Q,x)=.36x and
R=max(R,delta x), including endpoint delta x, has the same qualified properties.
These are real-function properties only. They do not prove implementability,
participation, volume improvement or optimality. They cannot be ported unchanged
to r=1.25 or to a dust-fallback EVM without a separate design proof.

## P6. Producer global optimum and corrected comparative statics

Assume fixed Delta, eta>0,k>0,c>=0,L>=0,b0>=0,beta in [0,1]. The cash constraint is
ky^2/2+cy-L<=0. Its nonnegative feasible set is

    0<=y<=(sqrt(c^2+2kL)-c)/k.

Profit is eta(b0+beta Delta)y-cy-ky^2/2. Its first derivative is
eta(b0+beta Delta)-c-ky and second derivative is -k<0.
Consequently the unconstrained stationary point is [eta(b0+beta Delta)-c]/k,
and projection onto the closed feasible interval gives the unique global optimum
in the master specification, including the singleton interval when L=0.

If beta=0 and L and all other primitives stay fixed, output is independent of Delta.
If Delta=max(0,P(1-d)-g_s/x-v) with fixed x, Delta>0 and
0<y*<(sqrt(c^2+2kL)-c)/k, then

    dy*/dd = eta beta/k * (-P) = -eta beta P/k.

The recovered Gate 12 appendix already states the positive-output/slack-cash
conditions and generalizes to fixed success probability pi. Its premium is
max{0,pi[P(1-d)-g_s/x-v]-(1-pi)g_f/x}; the corresponding interior derivative is
-eta beta pi P/k. This gate retains that qualification; it does not claim a new
correction to the original appendix.

It is strictly negative only if beta>0. At the output-zero or cash-constrained
interior of its regime it is zero; at kinks no ordinary two-sided derivative is asserted.
Projection onto an interval is increasing and 1-Lipschitz. Therefore for Delta1>=Delta0,

    0 <= y*(Delta1)-y*(Delta0) <= eta beta (Delta1-Delta0)/k.

This result fails as a closed-form production solution if Delta is a function of y.
Later token receipts do not relax the assumed fixed pre-production L. If those
receipts are pledgeable and finance changes, a financing game must be added.

## P7. Identification limitation

Even with an observed interior y and known eta,c,k, production implies only
b0+beta Delta=(c+ky)/eta. With unknown b0 and beta, many pairs can satisfy this
equation (whenever the parameter restrictions admit them). Corner output provides
inequalities and is no more identifying. Fee-recipient shares constrain a different
allocation rule and do not supply the missing commercial-contract equation.
Thus the observations alone do not generically point-identify beta. This is an
identification limitation, not an estimated confidence interval or identified set
without explicit observed data and measurement assumptions.

## P8. Finite designer existence and scope

Each declared scenario has six amount actions including abstention. Removing infeasible
actions leaves at least abstention. The deterministic tie rule selects a best response.
There are seven declared policies. S0 meets its own weak HHI and 70% fee-floor constraints,
so the feasible policy set is nonempty. A finite set of objective values has a maximum.
Enumerating every policy and every amount action therefore finds the global maximum
OF THIS FINITE NUMERICAL PROBLEM. Decimal evaluation is numerical, not an interval
certificate for the continuum real-function problem. No result about an omitted
policy, private-type IC, endogenous-price equilibrium or environmental welfare follows.

## P9. Remaining Gate 9 small-trade and redemption-inventory claims

For redemption 0<x<Q and x<=q_j, replace q_j by q_j-x and Q by Q-x in HHI.
Expanding exactly as in P3 gives

    H_after-H=[2Qx(H-q_j/Q)+x^2(1-H)]/(Q-x)^2.

Its denominator is positive. Concentration increases iff
q_j/Q < H+x(1-H)/(2Q). This is accounting, not an incentive theorem.

Set s=q/Q in (0,1). Differentiate the real deposit/redemption formulas with
respect to x at x=0. For deposit, the post-trade share has derivative (1-s)/Q;
for redemption it has derivative -(1-s)/Q. Product and chain rules yield

    mu_D(s)=.18[-log10(1-.99s)+.99s(1-s)/((1-.99s)ln(10))],
    mu_R(s)=.30[log10(1.10/(s+.10))-s(1-s)/((s+.10)ln(10))].

Differentiating these one-variable functions and collecting over common
denominators gives respectively

    mu_D'(s)=.18*.99*(1-s)*(2-.99s)/((1-.99s)^2 ln(10))>0,
    mu_R'(s)=-.30*(1-s)*(s+.20)/((s+.10)^2 ln(10))<0.

All factors in the stated denominators are strictly positive. These are real
small-trade slopes, not guarantees about minimum executable wei amounts.

## P10. Gate 10 quadratic asymptotics

For an absent project q=0 and fixed Q>0,

    D(0,Q,epsilon)=-.18 epsilon log10(1-.99 epsilon/(Q+epsilon)).

Using -ln(1-z)=z+O(z^2) and epsilon/(Q+epsilon)=epsilon/Q+O(epsilon^2)
gives D=.18*.99 epsilon^2/(Q ln(10))+O(epsilon^3).

For fixed q>x>0, expand at positive z:

    z log10(z/(z+epsilon)+.10)
      =z log10(1.10)-epsilon/(1.10 ln(10))
       +epsilon^2[1/1.10-1/(2*1.10^2)]/(z ln(10))+O(epsilon^3).

This follows by substituting z/(z+epsilon)=1-epsilon/z+epsilon^2/z^2
+O(epsilon^3) into ln(1.10+t)=ln(1.10)+t/1.10-t^2/(2*1.10^2)+O(t^3).
Apply at z=q-x and z=q, subtract, and add x log10(1.10). Constant and
first-order terms cancel. Since 1/(q-x)-1/q=x/[q(q-x)],

    R(q,q+epsilon,x)
      =.30*x*epsilon^2[1/1.10-1/(2*1.10^2)]/[q(q-x)ln(10)]
       +O(epsilon^3).

The coefficient is positive. Fixed-point EVM arithmetic can still round, reject
or activate dust fallback at finite epsilon; the expansion does not override that.

## P11. Anchored smoothing cannot preserve the intended monotonicity

For fixed Q>x>0 and tau>0 set lambda=(Q-q)/(Q-q+tau Q). Its limit as q increases
to Q is zero. A blend (1-lambda)*.10x+lambda*F with the real source fee F
therefore has boundary value and limit .10x because F has a finite limit.

For deposit the interior limit of F is .36x>.10x. Thus sufficiently close to Q,
F>.10x and lambda>0, making the blend greater than its endpoint value .10x.
That contradicts nondecreasingness on any such interval including Q.
For redemption, F tends to 0<.10x, so the blend lies BELOW its endpoint value
near Q, contradicting nonincreasingness. This proves the original Gate 11
smoothing objection without relying on the numerical grid. It establishes neither
an exploit nor the economic accessibility of arbitrary near-boundary states.
