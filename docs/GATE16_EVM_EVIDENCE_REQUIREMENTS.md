# Gate 16 — EVM Verification Evidentiary Protocol

## Research isolation
This PR targets ONLY `research/char-refi-standalone`. Do not merge into old `main`.

## Claims and evidence gates

1. **Published source code**: Toucan `dynamic-fee-pools` commit `7aef954dae1bd0c7add4ed66d216251110521b16`. Source baseline (README): deposit ratio scale 0.99, deposit scale 0.18; single-project fee 0.10. Source evidence **is not deployed-parameter evidence**.
2. **Source-level EVM tests**: `forge test --match-path test/SourceCHARBoundary.t.sol -vvvv`; require compiler output and complete test logs. Failed tests must cause nonzero process exit.
3. **Forked EVM tests**: `forge test --match-path test/DeployedFeeCalculatorFork.t.sol --fork-url "$BASE_RPC_URL" --fork-block-number <documented_base_block>`. The test probes actual recipients and parameter values **without hardcoded address/share assertions**; writes the observed result. This step requires an RPC capable of historical EVM state.
4. **Proxy implementation matching**: at SAME historical block, read ERC-1967 implementation and/or beacon slot, pool `feeCalculator()`, FeeCalculator runtime bytecode, `getFeeSetup()`, configuration parameters, filter and eligibility.
5. **Transaction reconciliation**: verify receipt `status`, block, event logs, and token mint/transfer accounting. An end-of-block snapshot is NOT an intra-block pre-transaction state; use trace/replay as needed.
6. **Economic attribution**: project-specific producer revenue sharing `beta` cannot be inferred from a token recipient wallet alone. Private commercial contracts or independent recipient attribution are needed.

## Critical hypothesis to verify, not assume

An earlier fork test asserted `depositFeeRatioScale == 1.25e18` at Base block 58,258,072. This value has NOT yet been independently validated by a live RPC receipt/state call. If true, the dynamic deposit branch's requirement `resultingRatio * depositFeeRatioScale < 1` imposes a ~80% post-deposit project-share cutoff. This materially changes conclusions from simulations using 0.99. **Do not report the cutoff as actual deployed policy until read from chain.**

## GitHub Actions

Draft PR intentionally triggers workflow `pull_request` targeting `research/char-refi-standalone`, not old `main`. Test logs and artifact files must be checked before claiming EVM PASS.

Status as of this document: **PENDING — no verified Foundry run or mainnet fork logs**.
