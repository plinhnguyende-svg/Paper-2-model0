# Gate 24 — bounded CHAR event discovery and receipt accounting

Date: 2026-11-17. Research branch: `research/char-evm-verification-pr`; draft PR #21 targets `research/char-refi-standalone` (NOT legacy main).

## What ran

- GitHub Actions `CHAR historical RPC and receipt evidence`, run [44021263614](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/runs/44021263614) on commit `f9b8b18d474f8ac9f601c7126e9e5cc743e51940`: **SUCCESS**.
- Independent Foundry validation run [44021263621](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/runs/44021263621) on same commit: **SUCCESS**.
- Actual data artifact: [char-actual-receipt-evidence, id 14300713729](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/runs/44021263614/artifacts/14300713729), ZIP SHA-256: `738553373300410b3c4e67dcd2a5e356e1ca7e928bf3464f5244d846ac71616b`.
- Repo unit tests: `test_char_event_windows.py` covers adaptive split, failed coverage budget, scope checks, candidate deduplication, and canonical event/receipt match. All passed during this run. All receipt amounts below are raw integers, **not USD or financing payments**.

## Exact scope and coverage

The independent `eth_getLogs` query uses an OR-filter over five POOL-emitted topics: DepositFeePaid, Deposited, RedeemFeePaid, RedeemFeeBurnt, Redeemed. No mint-only nomination is necessary to select these event candidates.

| Start block | End block | Inclusive blocks |
|---:|---:|---:|
| 13,826,150 | 13,826,650 | 501 |
| 15,709,320 | 15,709,820 | 501 |
| 58,257,800 | 58,258,072 | 273 |
| **Total** | | **1,275** |

`SCAN_LEDGER.json`: 68 successful leaf scan intervals, 1,275 of 1,275 blocks accounted for. The scanner made 70 `eth_getLogs` RPC calls; provider-level `RPC_FAILURE_TYPES.json` records 13 failures, handled by fallback/adaptive subdivision. No unscanned gap remains **within these declared windows**.

`EVENT_LOGS.json`: 7 queried event logs, 3 distinct transaction candidates. `EVENT_RECEIPT_RESULTS.json`: 3 of 3 candidates had successful canonical block/transaction/receipt identity and raw fee+token accounting; zero verification errors. The sampler limit of 48 was not reached.

## Reconciled historical receipts

| Type | Transaction | Block | tx index | amount_raw | fee_raw |
|---|---|---:|---:|---:|---:|
| Deposit | `0x0237beb377836c8ca1bec693cc5d37eff65d3a48b53b68d667fed67839b8193c` | 13,826,401 | 27 | 18000000000000000000 | 299055716169059513 |
| Deposit | `0x6d2d4967ab52981478ad0fe552ae0cfa3ca22a07067d48ec9055dbf883c96f82` | 15,709,568 | 60 | 50000000000000000 | 1152207307360887 |
| Redemption | `0xc676a373fc6cec24dd9f744f04a7dd7f975921370be6270185006b25fbd4f034` | 15,709,581 | 52 | 5000000000000000 | 9412065557460 |

For the deposits, underlying transfers into pool, total CHAR minted, depositor net mint, and fee-recipient mint accounting each match the emitted events. For the redemption, pool burn, fee-token transfers and underlying transfer out of pool match the emitted events. `targeted_events/SHA256.json` was independently checked against all 18 listed files: zero digest mismatches. These are **receipt accounting identities only**.

## Critical unresolved gates

1. **Exact fee formula at execution:** Need active proxy implementation and FeeCalculator code/configuration plus inventory **immediately before tx index**. End-of-block and block-minus-one snapshots are insufficient when earlier same-block transactions modify state. `prestateTracer` availability in a separate deposit sample is not itself a reconciled formula.
2. **Whole-history coverage:** These three narrow windows and 3 receipts do not represent all CHAR transactions or fees, nor claim statistical sampling. Persist chunk-ledger pagination/census strategy and failure accounting before generalizing.
3. **Source/deployed identity:** Previously pinned upstream Solidity is not yet proven bytecode-identical to active implementation at each historical receipt.
4. **Beneficial owner/economic transmission:** Recipient addresses, commercial fee-sharing, `beta`, cash realization, pre-production funding, physical output and CDR additionality remain unverified. Credit receipts cannot identify producer financing.
5. **Institutional comparison:** Conventional fee-setting/clearing benchmark and smart-contract governance/upgrade rights require explicit modeling; they are not established by receipt evidence.

Next technical gate: transaction-index-aware prestate/implementation reconstruction for **one matched deposit and one matched redemption**, with explicit failure labels if trace/replay cannot provide exact prestate. Compare computed fee and per-recipient rounding to raw receipts only after state and version are validated.

**Interpretation:** Gate 24 establishes bounded event discovery and canonical receipt accounting, not mechanism welfare, exact on-chain fee reproduction, or a blockchain-specific institutional advantage.
