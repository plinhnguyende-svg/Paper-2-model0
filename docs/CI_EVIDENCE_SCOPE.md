# EVM validation evidence checklist (not to merge into previous Paper 2)

This PR targets ONLY the isolated `research/char-refi-standalone` branch.

## Source-level test claims

- [ ] GitHub Actions CI job executed and passed using Foundry
- [ ] Upstream FeeCalculator pinned to Toucan commit `7aef954dae1bd0c7add4ed66d216251110521b16`
- [ ] 10% single-asset branch observed in EVM units
- [ ] Exact 60/40 recipient allocation on test fixture
- [ ] 1 wei–1 TCO₂ near-boundary grid reports reverts and fee units
- [ ] CI artifacts retained (log, pinned dependency commits)

## Deployed-contract claims (SEPARATE)

- [ ] Base historical proxy implementation matched by block
- [ ] FeeCalculator address matched by block
- [ ] Same-block fee parameter and FeeSetup snapshots
- [ ] Historical receipt and token transfer events reconciled
- [ ] Source-runtime bytecode correspondence verified
- [ ] Verified project/producer identities and contractual pass-through, if claimed

**No PR merge is necessary to inspect checks.** A passing source-level EVM test
does not imply deployed source or producer-royalty evidence.
