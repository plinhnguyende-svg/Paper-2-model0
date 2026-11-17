# Gate 18 — Master specification v1.0

Date: 2026-11-17. Track C1. This is a consolidated analytical specification,
with original Gates 9–13 packages recovered and their main numerical workflows replayed.
Numerical replay does not certify every original theorem or historical execution.
Repository base: `7e2521e3ddefdb48f6e0551d7d1f6f255f49d7ea`.

## 1. Research question and evidence boundary

How do inventory-dependent transaction rules and financial allocation affect
participation, execution and value transmission in biochar carbon-removal supply chains?
Baseline method: partial-equilibrium economic rule design with individual optimization.
No hidden-type report, revelation mechanism, Bayesian IC theorem or multi-trader Nash
equilibrium is assumed. A designer anticipating best responses can be studied without
claiming a fully strategic market equilibrium or a blockchain-superiority theorem.

Use separate evidence labels: R (real-number derivation), E (source EVM),
D (deployed-calculator checkpoint), T (actual pool transaction), S (synthetic experiment),
C (conditional contract/producer extension). No implication R -> E -> D -> T is automatic.

## 2. Agents, rights, information and timing

Agents: designer with authority over the modeled rule; credit holder/intermediary;
buyer redeeming underlying credits; configured recipients; optional upstream producer.
Legal credit owner, on-chain holder, depositor, recipient and producer are distinct roles.
The baseline trader is disjoint from recipients. An overlap extension is explicit below.

0. Designer commits to a rule for one modeled horizon, using only public state.
   This is a modeling assumption, not an assertion that the upgradeable pool is immutable.
1. Trader observes initial inventory, quote rules, outside values and success/failure costs.
2. Trader chooses abstention or an eligible project, amount and positive fee cap.
3. Exogenous state shocks may occur between quote and execution. Their distribution
   is fixed independently of the trader's cap; strategic order flow is outside baseline.
4. The pool executes the appropriate branch if all checks and the cap pass; otherwise
   the transaction reverts. Failed transactions retain underlying holdings but cost gas.
5. Successful tokens and fees are allocated, inventory updates, and economic value is
   evaluated at an exogenous price P > 0, with sufficient exit liquidity assumed.

The computational baseline is the deterministic, immediate-execution special case.
Each scenario is an independent one-trader decision, not a trajectory of simultaneous
or sequential strategic participants. The uncertain-cap problem is proved separately.

## 3. State, units and feasible actions

Inventory q_j >= 0 is aggregated at PROJECT level, with Q = sum_j q_j > 0.
Multiple vintages of one project must not be counted as independent projects.
Amounts x are normalized underlying-credit units; fee F is in normalized CHAR units.
One-to-one mint/burn is assumed only for the accounting path inspected in published
pool source. Code elsewhere may override it. All cash terms use one currency.

State also includes implementation, active calculator, parameters, recipients,
shares, eligibility/filter, pause, cap, seeding, exemptions, balances and allowances.
Baseline: eligibility, balances and allowances satisfied; unpaused; no cap truncation;
pool above seeding threshold; no exemption; active calculator; no price impact.
These are scope assumptions, not observations that all historical transactions satisfy them.

General executable set A(state,rule) requires the whole pool path. Calculator domain
is necessary only when that calculator is actually called, and is not sufficient.
Strict domain boundaries can produce open feasible sets and nonattainment in a
continuous model. Do not assume a continuous argmax exists without proof.

Computational actions: abstain or deposit x in {0.25,1,2,5,10} of the trader's
specified project. A finite action set guarantees existence. Tie breaking: abstain
at zero profit; otherwise smallest quantity among equal maximizing quantities.
No cross-project switching by a trader who does not own those credits is allowed.
HHI is undefined for Q=0; empty pools require a separate seeding model.

## 4. Payment accounting and outside options

Source references: ToucanProtocol/contracts at
`9afe1809bd4840cad82fc49d26d8286a7c6728e1`, Pool.sol,
PoolERC20able.sol, PoolWithFeeCalculatorERC20.sol.
These paths are source accounting, not exact historical bytecode matching.

Deposit: trader supplies x underlying; x-F CHAR minted to trader and total F minted
to recipients. Total mint is x. Inventory increases by x, not x-F.
Redemption-out: trader receives x underlying and spends x+F CHAR; x is burned for
underlying withdrawal. Gross fee is divided into recipient net transfers and a
configured transfer to the burn address. Transfer-to-burn-address is not automatically
an ERC20 supply burn. Per-recipient RedeemFeePaid events can be net of this component.
Receipt reconciliation must include the burn-address transfer and rounding.

For integer fee F_w and percent weights a_r summing to 100:
gross_r=floor(F_w a_r/100), then recipient 1 receives F_w-sum gross_r residue.
Redemption burn_r=floor(gross_r B/D); net_r=gross_r-burn_r.
Sum net_r + sum burn_r = F_w. Thus a_r F is only a real-number gross allocation,
not an exact per-recipient EVM payment identity.

Holding/selling outside the pool normalizes abstention payoff to zero. Let v be
the opportunity value per underlying credit owned by a depositor; let u be the
redeemer's willingness to pay per underlying credit. These are fixed cash valuations.
Successful baseline payoffs are

    U_D = P(x-F_D) - v x - g_s,
    U_R = u x - P(x+F_R) - g_s.

Existing assets are not treated as free, and fee tokens are not subtracted twice.
If the trader receives fraction a of the gross deposit fee itself, replace F_D by
(1-a)F_D. For redemption, use the trader's NET entitlement after burn/rounding,
not automatically a F_R. Baseline economic claims require disjoint trader/recipients.
Allocation percentages and contractual producer pass-through beta are different objects.

At exogenous P and disjoint recipients, changing only recipient shares while holding
the total fee and all other behavior fixed cannot change the trader's participation.
Claims that allocation itself changes participation need ownership overlap, recipient
decisions, pass-through or a priced externality. Otherwise it is pure redistribution.

Do not add fee receipts to participant surplus and then call the sum new financing
or environmental welfare. With fee recipients included, fee transfers cancel in
the simple accounting identity; endogenous prices and externalities are separate.

## 5. Two benchmarks, not one blended mechanism

Machine-readable provenance: config/benchmarks.json.
S0: published source pinned to dynamic-fee-pools commit
`7aef954dae1bd0c7add4ed66d216251110521b16`: deposit scale .18,
ratio .99, redemption scale .30, shift .10, single-project rates .10.
H0: observed Base block 58,258,072: deposit scale .15, ratio 1.25,
calculator 0x6A4549759C475d845d4AE074B3656dC257490DA5 active for CHAR in fork tests.
Checkpoint recipient configuration 75/25 does not identify producer ownership.

Applying H0 parameters to S0 formulas creates a PARAMETERIZED COUNTERFACTUAL.
It does not prove H0 source-bytecode equivalence or define a complete deployed oracle.
Observed checkpoint values are not a continuous governance history.
The source EVM dust fallback must not be overwritten by an ideal real-number limit.

## 6. Participant response and designer problem

For rule p and scenario w, choose a*(p,w) from the finite feasible actions plus
abstention to maximize U_D. Participation is endogenous; quantity is endogenous on
the declared grid; price, opportunity costs and inventory before this one action are fixed.

Implemented designer chooses among seven rules: flat 1%,5%,10%,20%,35%; S0 real
formula; S0 formula with H0 deposit parameters. The latter remains a counterfactual.
The flat policies are proposed designs, not historical policies.

Maximize sum_w x*(p,w), equally weighting 36 synthetic scenarios, subject to:

    H_after(p,w) <= H_after(S0,w) + .02 for every scenario w;
    sum_w F(p,w) >= .70 sum_w F(S0,w).

The fee-budget and HHI limits are researcher-chosen engineering constraints, not
estimated preferences, producer support or a welfare optimum. Baseline S0 is feasible.
Exhaustive numerical enumeration certifies only this specified finite candidate set,
under its Decimal arithmetic and deterministic tie rule. It is not a continuum
optimization theorem, not a unique-optimum theorem, and not an empirical ranking.
Allocation weights are fixed; optimizing them without a behavioral channel is degenerate.
An uncertain-state version can maximize expected utility over (amount,cap,abstain),
but is not the experiment implemented here.

## 7. Conditional producer extension

Before production, a contract fixes b=b0+beta Delta per verified credit, with beta
in [0,1], Delta >= 0 treated as a FIXED expected monetization premium per unit.
Producer chooses y >= 0, cost cy+ky^2/2 with c >= 0,k > 0, verified yield eta > 0,
and pre-production cash L >= 0 imposing cy+ky^2/2 <= L. No advances or collateral
against later tokens are available. All dates are valued at the same numeraire;
discounting, verification risk and ancillary biochar revenue are omitted explicitly.

    y* = min{(sqrt(c^2+2kL)-c)/k,
             max{0,[eta(b0+beta Delta)-c]/k}}.

The price-taking/fixed-premium assumption is ESSENTIAL. If x=eta y and a producer's
own output changes inventory-dependent fees, Delta=Delta(y) and this quadratic
closed form is no longer the solution in general. Baseline and extension are therefore
conditional modules, not a claimed fully closed supply-chain equilibrium.

If Delta=max{0,P(1-d)-g_s/x-v} for a fixed lot x, the strict derivative
dy*/dd=-eta beta P/k holds only when Delta>0, beta>0 and 0<y*<cash limit.
No derivative claim at participation/cash kinks; output-zero corner also has zero response.
Changing only later fee receipts does not increase a fixed L.
Beta is not identified by fee events or issuance alone, and is never set to .75 or .25
because those are recipient shares. No direct producer royalty is assumed in this extension.

## 8. Acceptance and outstanding work

Formal consolidation: provided in this document and GATE18_PROOFS.md.
Historical evidence: inherited checkpoint evidence, not new live extraction.
Original Gates 9–13 code/appendices recovered; selected unmodified originals are
preserved under validation_inputs/. Main runs regenerate 27 archived CSVs with
numerical agreement at rtol=atol=1e-10; see original_replay_manifest.json.
Original policy rankings remain finite-grid synthetic results, not functional
optimality. Empirical calibration, endogenous pricing,
strategic ordering and governance equilibrium remain outside this gate.
Transaction reconciliation remains a separate, explicitly non-PASS evidence gate.
