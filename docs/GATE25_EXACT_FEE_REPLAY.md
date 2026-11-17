# Gate 25 — transaction-index-aware historical FeeCalculator replay

Date: 2026-11-17. Draft PR #21; research branch `research/char-evm-verification-pr`. No merge to old `main`.

## Verification verdict

**PASS — exact deployed-EVM calculator quotation matches a known historical deposit and a known historical redemption, including fee-recipient integer rounding.**

- Canonical passing GitHub Actions run: [44023361157](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/runs/44023361157), source commit `4d61325030e0fb2ff3d064e755cd6db867683124`.
- Test: [HistoricalCHARExactFeeFork.t.sol](../test/HistoricalCHARExactFeeFork.t.sol), 2 PASS / 0 FAIL with full passing traces (`forge test --via-ir -vvvv`).
- [Archived full-trace artifact 14301812048](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/runs/44023361157/artifacts/14301812048), containing `EXACT_FEE_REPLAY.log`, dependency pin manifest and Base RPC preflight output.
- Receipt evidence independently obtained in [Gate 24](GATE24_BOUNDED_EVENT_RECEIPT_AUDIT.md), run 44021263614, is **not** generated from the FeeCalculator under test.

### Why the pre-transaction state is valid

`vm.createSelectFork(BASE_RPC_URL, txHash)` reconstructs the historical block with preceding transactions replayed, immediately before the selected transaction. It is not an `eth_call` at B-1 or at the end of B. A failure in this replay causes test failure. Base chain id 8453 and historical access had already passed the RPC preflight.

Historical pool proxy: `0x20b048fa035d5763685d695e66adf62c5d9f5055`.

The Gate 24 deposit `callTracer` exposes an important historical ABI distinction:
- TCO2 metadata getter selector `0x3633f35f` returns a dynamic tuple; the fourth static tuple word identifies the on-chain project ID. The test validates the ABI offset and requires a positive ID.
- The active pool's project inventory getter uses selector `0x875bf3b5` with the **project ID as uint256**, not `totalPerProjectSupply(address)`; the latter reverts under this implementation.
- The active FeeCalculator selected the deployed historical getter. Our EVM test retrieves this actual project-specific inventory independently, then invokes its deployed fee-calculation method with the observed TCO2 address and exact amount.

No alternative assumed ERC20 balance or after-transaction snapshot replaces inventory.

## Exact historical states and fees

Every amount below is in raw 18-decimal units unless indicated otherwise. Scaling by `1e18` is display only, **not a statement of USD value or financing**.

| Item | Deposit | Redemption |
|---|---|---|
| Transaction | `0x0237beb377836c8ca1bec693cc5d37eff65d3a48b53b68d667fed67839b8193c` | `0xc676a373fc6cec24dd9f744f04a7dd7f975921370be6270185006b25fbd4f034` |
| Block | 13826401 | 15709581 |
| Transaction index | 27 | 52 |
| TCO2 token | `0x99f5f445ff1f537686f2fbc32d43653c7c786645` | `0xf20cb470acda661ab02de3b7be43894e2ade0b1c` |
| Project ID | 13 | 6 |
| Total pool inventory (raw) | 81950000000000000000 | 594950000000000000000 |
| Project inventory (raw) | 0 | 499000000000000000000 |
| Amount (raw) | 18000000000000000000 | 5000000000000000 |
| Expected/quoted total fee (raw) | 299055716169059513 | 9412065557460 |
| Fee recipient 0 amount (raw) | 224291787126794635 | 7059049168095 |
| Fee recipient 1 amount (raw) | 74763929042264878 | 2353016389365 |
| Fee unit rounding remainder assigned to recipient 0 | 1 | 0 |
| Result | EXACT MATCH | EXACT MATCH |

The two historical fee recipients were:
- `0x7d3e7bbd4e9e4e1507ff4a4b488934abfbacb801` — 75%.
- `0xca07b1b8a2d6767178f7f7038a3c54ac949d9440` — 25%.

Actual per-recipient transfers are independently verified in Gate 24. For total fee `F` and configured weights `s_i` with `sum(s_i)=100`, the published source's integer sharing uses `floor(F*s_i/100)` for each recipient and assigns any remaining integer units to the first recipient. Gate 25 checks both this separate rounding identity and equality of **each** deployed-quoted share with actual receipt tokens.

## Historical deployed contracts and parameters

Both pre-transaction states:
- EIP-1967 pool implementation: `0xb61763cf40e53df924856925461d5914c274ecd8`.
- Pool implementation code hash: `0x9e01a24f7396330a59b37961a59c3ea2db412674f62570fdbb29bb0c73204c80`.
- Active FeeCalculator: `0x6a4549759c475d845d4ae074b3656dc257490da5`.
- Active FeeCalculator code hash: `0x18a0f3dc9ce66d94741ad4e13edf136a497154f96c828bfa9148bc0591a1900b`.
- `depositFeeScale`: `150000000000000000` (0.15).
- `depositFeeRatioScale`: `1250000000000000000` (1.25).
- `redemptionFeeScale`: `300000000000000000` (0.30).
- `redemptionFeeShift`: `100000000000000000` (0.10).

Crucially, published upstream source pinned to commit `7aef954dae1bd0c7add4ed66d216251110521b16` defaults to deposit scale 0.18 and ratio scale 0.99. The two historical deployed parameter values above reflect actual pre-transaction state; defaults in published source are **not** valid historical calibration. Parameter differences alone do not establish a code mismatch, since owner setters can modify configuration.

## What PASS does and does not mean

1. **Proven on two transactions**: actual pre-tx proxy/calculator identity and callable EVM state; project-specific inventory; selected fee parameters; active deployed-EVM fee quotation; raw per-recipient amount and integer rounding equal the canonical receipts.
2. **Not proven**: deployed runtime bytecode equivalence to the *pinned public source compiler artifact*, and equality across every historical proxy upgrade. This requires full build and deployed bytecode provenance beyond two code hashes.
3. **Not proven**: all pool execution branches, all transactions, failed attempts, complete transaction coverage, or causal market outcomes.
4. **Not proven**: beneficiary/producer identity, commercial revenue pass-through `beta`, early cash funding, increased physical CDR or a blockchain-specific superiority theorem.
5. **Method classification**: deployed-calculator EVM *re-quotation at exact prestate*, corroborated by independent event/receipt accounting; not an independent pure-mathematical reimplementation of every fixed-point/logarithmic PRB operation and not proof that source code perfectly matches deployed bytecode.

## Next gates

- **Gate 26 (technical):** match source+compiler+library configurations to historical runtime bytecode, explicitly account for proxy implementation changes and FeeCalculator governance updates; then test the formula through an independently compiled exact-source build where meaningful.
- **Coverage:** define a complete chain/address/date universe and paginated event census; treat fee-carrying windows as examples only until complete.
- **Economics:** keep sender, depositor, fee-recipient, CORC owner, project producer, and physical output as distinct entities; identify `beta` only from independent commercial evidence. Preserve a capable conventional clearinghouse benchmark.
