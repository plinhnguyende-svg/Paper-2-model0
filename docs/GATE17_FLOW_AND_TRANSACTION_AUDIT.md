# Gate 17: economic-flow audit and real-transaction evidence
Date: 2026-11-17. Baseline: 060c63b33d0befefef7648c48d8fadd6e18f14ba.

## Verdict before this run
Gate 16 source tests and deployed calculator tests really passed in run 44000844914
(job 133764208799: 5 source tests, 4 fork tests). But suite counts do not measure
all economic properties. This branch does not yet establish a complete main theorem,
an optimal mechanism, producer financing, or additional removal.

## Corrections implemented
1. A fork failure now fails its CI step rather than ending with a successful echo.
2. The deployed grid now uses MockTCO2 consistently, not an EOA on deposits.
3. The pinned checkpoint must have the published calculator active for CHAR.
4. The grid asserts the expected domain-error reason and single-project fee.
   Redemption grid entries remain observations, not numerical correctness assertions.
5. Discover actual pool mint/burn candidates in a fixed stated block window,
   retain canonical receipt/block identities and raw ERC20 transfers, attempt native
   call/prestate tracing and index-aware cast replay, and archive SHA256 checksums.
   Collection success is NOT fee reconciliation success.

## Economic sequence that must be kept distinct
1. Governance chooses fee parameters, recipients, eligibility and upgrade authority.
   The fee owner can change rules; an immutable commitment assumption requires a
   separate governance model or explicitly fixed horizon.
2. Physical biochar production and MRV precede verified removal issuance.
   Exact legal custody, registry rights and tokenization timing require evidence.
3. CORC owner authorizes tokenization/custody and may transfer rights to an intermediary.
   Producer, credit owner, depositor and fee recipient are separate roles, even when
   one entity happens to perform several.
4. Intermediary observes inventory, eligibility and current fees; chooses transaction
   amount, project, timing, outside venue or abstention. In a multi-agent model,
   transaction order and anticipated inventory changes must be specified.
5. Actual pool logic checks pause/cap/filter/allowance/balance and exemption/seeding
   branches, then invokes a calculator where applicable. Exact call order and fee
   charging units must be verified from the active implementation/trace.
6. A successful transaction changes TCO2 inventory and CHAR balances; failed execution
   rolls back state but may consume gas. Distinguish calculator quotes from execution.
7. Fee recipients obtain the tokens shown by actual transfers. Token receipt is not
   automatically a cash payment or upstream financing.
8. Producer receives only what enforceable commercial pass-through delivers. Keep beta
   unestimated; beta=0 is admissible. Timing and liquidity/cash realization matter.
9. Future producer effort/output may respond only to anticipated net cash flows and
   production costs. Retirement is distinct from physical additional removal.

Material flow: feedstock -> biochar -> eligible end use/storage.
Information flow: MRV -> certificate -> registry/token linkage -> pool eligibility.
Financial flow: credit acquisition -> tokenization/deposit/redemption -> token fee allocation
-> optional sale/cash settlement -> contractual producer payment.
These flows are asynchronous; token issuance does not itself fund earlier production.

## Formal primitives required before equilibrium claims
State includes per-project inventories (not necessarily per-vintage balances), active
implementation, fee parameters, eligibility, exemptions, balances and transaction order.
An action is amount/project/venue/timing/abstain. Define the executable action set using
the whole pool, not only the calculator's logarithm domain. Payoffs include acquisition
cost, CHAR valuation or demand, gas, slippage, outside options and expected pass-through.
Then solve best responses/equilibrium under a specified information structure.
Only call the paper mechanism design when a designer optimizes an explicit objective
over admissible rules subject to participation, incentive and execution constraints.

## Domain result: necessary corrections
In the dynamic deposit branch with ratio scale 1.25, the real-number condition is
(current + amount)/(total + amount) < 0.8.
For a nonnegative amount and current < total, this implies
amount < 4*total - 5*current. This is a domain restriction, not a complete
execution condition: zero-fee, fee-exceeds-amount and pool checks can also reject.
The current==total branch bypasses this dynamic condition and applies its own fee.
Thus the 80% statement is not a universal cap on project representation.
At the exact threshold use fixed-point EVM arithmetic, not a real-number approximation.
Boundary state perturbations need not be reachable economically: adding a second project
requires eligible assets and transaction costs, not an arbitrary free dust operation.

## Gate 17 acceptance criteria
A. Deterministic transaction selection + canonical receipts + tx indices.
B. Actual deposit and redemption identified from active implementation ABI and traces;
   mint/burn logs alone only nominate candidates. State sample limitations explicitly.
C. Exact intra-block prestate via trace or replay of preceding txs; block B-1 is insufficient.
D. Actual active calculator, parameters, exemption/seeding state and implementation linkage.
E. Predicted fees in correct token units equal decoded fee events and actual transfers,
   including per-recipient integer rounding, mint/burn accounting and TCO2 movement.
F. Separate failures due to fee domain from failures due to eligibility, allowance or pause.
G. Recipient identity and commercial transmission remain separate evidence gates.

Current collector addresses A and gathers inputs toward B-E. It does not automatically
award B-E. Successful mint/burn samples cannot identify the incidence of excluded
transactions, failed user attempts, welfare losses or strategic behavior.

## Research contribution discipline
Supported direction: economic design of programmable transaction fees and feasible
transactions in tokenized carbon-removal supply chains.
Not yet supported: blockchain superiority, optimal governance, identified producer
financing, increased physical output, or causal carbon additionality.
A capable conventional institution remains a benchmark, not an assumed inferior technology.
Compare institutions through explicit commitment/control/cost primitives if that is
the intended contribution. Code boundary findings alone are protocol analysis.
