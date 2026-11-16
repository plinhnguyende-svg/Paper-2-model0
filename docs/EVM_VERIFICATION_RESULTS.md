# Gate 15 — Verified EVM and historical Base state (2026-11-16)

## Evidence, not speculative claims

1. **Source EVM**: GitHub Actions run [43893920881](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/runs/43893920881) — 4 tests PASS, including 256 fuzz runs; pinned Toucan source commit `7aef954dae1bd0c7add4ed66d216251110521b16`. Test fixture recipients 60/40 are synthetic.
2. **Deployed FeeCalculator fork**: run [43896128719](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/runs/43896128719) — 4 tests PASS at Base block 58,258,072. MockTCO2 implements `getVintageData()`; actual Base FeeCalculator handles fee-calculation requests and records a 75/25 distribution. Dominant deposit 100/101 TCO2 with additional 10 TCO2 rejected; minority deposit 10/100 with additional 10 TCO2 accepted. No real on-chain deposit was submitted.
3. **History**: run [43896484472](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/runs/43896484472) — archive reads and receipts confirm Upgraded event and ERC-1967 implementation slots before/after blocks 13,277,612 and 28,317,185.

## Base historical checkpoint table

| Block | Implementation | Pool VERSION | Active calculator | Fee scale / ratio scale |
|---:|---|---|---|---|
| 13,277,611 | zero slot | unavailable | unavailable | FeeCalculator artifact: 0.18 / 0.99 |
| 13,277,612 | 0xb61763cf40e53df924856925461d5914c274ecd8 | 1.0.0 | zero address | 0.18 / 0.99 (module not attached to pool) |
| 28,317,184 | 0xb61763cf40e53df924856925461d5914c274ecd8 | 1.0.0 | 0x6A4549759C475d845d4AE074B3656dC257490DA5 | 0.15 / 1.25 |
| 28,317,185 | 0x23da31aa73720f770c21e9ec0a8382ec279e0c85 | 1.1.0 | same calculator | 0.15 / 1.25 |
| 58,258,072 | 0x23da31aa73720f770c21e9ec0a8382ec279e0c85 | 1.1.0 | same calculator | 0.15 / 1.25 |

Historical reads are **end-of-block** states. Failed older-version getters must NOT be interpreted as zero inventory. An `Upgraded` event is verified by successful receipts and the implementation storage slot; exact within-block prestate of other transactions requires traces or index-aware replay.

## Actual FeeSetup

Historical transaction `0x1e4187be16964075654028ea7c92c02fc798d4bb097cab53efb5847cd85c91c0` succeeded at block **13,197,311** and set:
- `0x7d3E7BbD4e9e4e1507FF4a4b488934abfbAcb801` -> **75%**
- `0xcA07B1B8A2D6767178F7f7038A3c54aC949d9440` -> **25%**

The same setup is visible at the audited checkpoint blocks, but intermediate changes outside the checkpoints are not ruled out. Neither address is verified as a biochar producer. This is NOT evidence of producer cash payments or upstream investment.

## Economic / Solidity design correction

The pinned public FeeCalculator source has deposit `depositFeeScale=0.18` and `depositFeeRatioScale=0.99`. The deployed calculator in the tested 2025/2026 checkpoints is at **0.15/1.25**. Do not use the public-source defaults as empirical market parameters.

In the pinned source, near-dominance redemption returns 30% dust fee for sufficiently tiny second-project inventory on EVM, rather than the real-number limit of zero. For the deployed calculator, a high-share deposit can revert at fee calculation due to ratio-scale constraints rather than merely incur a high price.

Source EVM tests, deployed calculator mock-pool fork tests, and full market transaction behavior are three **different** evidence layers.

## Outstanding

- Source bytecode vs actual calculator runtime bytecode exact-match proof remains open; deployed `VERSION()` reverts.
- Reconstruct all historical fee parameter changes and FeeCalculatorUpdated events, not only checkpoints.
- Verify live deposits, redemptions, actual CHAR Transfer events and project-specific TCO2 inventories.
- Independently identify fee recipients, contractual pass-through `beta`, producer cash income, and physical biochar effects.

## Isolation

Only branch `research/char-refi-standalone` is used for CHAR. Previous N-H/S-H/F-H project on default `main` is not modified. For a truly independent repository, create an empty private repository and migrate this clean branch with new history.
