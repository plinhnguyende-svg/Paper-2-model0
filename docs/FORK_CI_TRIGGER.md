# Validation rerun: deployed Base fork

Target: only `research/char-refi-standalone`. Do not merge into old main.

At Base block **58,258,072**, test the actual deployed FeeCalculator at
`0x6A4549759C475d845d4AE074B3656dC257490DA5` against a local
mock pool. The fixture records observed 75/25 recipients, deposit scale
0.15, and ratio scale 1.25.

Evidence layers:
- The prior 4 source-level Foundry tests passed on GitHub runner.
- This PR update triggers a separate deployed-contract fork test.
- Historical upgraded proxy, FeeSetup, receipts, and actual CORC inventory
  require additional same-block/transaction-prestate reconciliation.

## Re-test after fixing EVM fixture
The deployed calculator calls TCO2.getVintageData; revised fixture supplies this ABI and a project ID. Test results are only valid if the real fixed-block fork run passes.

## Historical upgrade checkpoints
Re-run with public Base RPC to collect proxy implementation, calculator, fee parameters and upgrade receipts at 13277611/13277612 and 28317184/28317185. Every block call is independently marked OK/FAILED.
