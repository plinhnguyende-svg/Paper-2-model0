# Gate 26 — Source-to-Deployment Equivalence and Historical Provenance Audit

**Date:** 17 November 2026. **Repository:** `plinhnguyende-svg/Paper-2-model0`; draft PR #21 into `research/char-refi-standalone` (not legacy `main`).

## Verdict — three distinct evidentiary levels

1. **Audit execution: PASS.** The controlled GitHub Actions pipeline compiled four configurations of the originally pinned Toucan source, eight additional historical commit/configuration candidates, fetched historical Base runtime code at five declared snapshots, and matched two Gate 25 transaction-prestate codehash anchors.
2. **Originally pinned source `7aef954dae1bd0c7add4ed66d216251110521b16`: NOT MATCHED.** For Solidity 0.8.19, all four declared compiler configurations have **different executable code**, even after verified CBOR metadata separation. This is bounded negative evidence; it does not prove the source could never match under any other build environment.
3. **Historical alternative `1faac76f50db861331905391cb95b55d278391d9` (29 February 2024): EXECUTABLE PREFIX MATCHES.** Solidity 0.8.19 (0.8.19+commit.7dd6d404), **legacy non-via-IR**, optimizer enabled, **200 runs**, with the historical repo's gitlinked dependencies, generates precisely the same 12,395-byte executable prefix as the deployed FeeCalculator at all five checked snapshots. Solidity CBOR metadata differs, so this is **not an exact full runtime byte-for-byte match** and deployment build/input metadata provenance remains OPEN.

**Canonical Gate 26 run:** [44026059380](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/runs/44026059380) on commit `2704a07d1d9a764149672cb24a93b097b4f62197`. Successful workflow status denotes a successful audit procedure, **not** a success claim for the originally pinned source. Download [complete run artifact](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/runs/44026059380/artifacts/14302848343) (compiler artifact JSONs, immutable upstream commit manifest, per-candidate compilation logs, historical raw runtime hex, SHA-256 manifest, exact comparisons).

## Direct deployment provenance

The independent public Toucan [Base FeeCalculator deployment file](https://github.com/ToucanProtocol/contracts/blob/9afe1809bd4840cad82fc49d26d8286a7c6728e1/deployments/production/base/FeeCalculator.json) reports:
- Address: `0x6A4549759C475d845d4AE074B3656dC257490DA5`
- Creation transaction: `0x23e3050ea6498a843c5c7af7b171b0ccfbdcf29246e1914dbd0cc848ad25524b`

Gate 26 independently checked the Base mainnet receipt, contract creation address and canonical block identity:
- **Creation block:** `13163979`
- **Block UTC:** 2024-04-14 17:55:05 UTC (Unix `1713117305`)
- Receipt status: 1 (success)

Consequently, the candidate historical source dated 29 February 2024 is chronologically consistent with deployment. Later source revisions are not automatically historical deployment source. Timing is corroboration, not proof of source identity.

## Pinned build provenance and bounded comparison

Pinned published source: `ToucanProtocol/dynamic-fee-pools@7aef954dae1bd0c7add4ed66d216251110521b16`.

Exact upstream gitlinked submodule revisions (checked before building and captured in artifact):
- OpenZeppelin Contracts: `d4fb3a89f9d0a39c7ee6f2601d33ffbf30085322`
- PRB Math: `77fa88eda4a4a91b3f3e9431df291292c26b6c71`
- forge-std: `f73c73d2018eb6a111f35e4dae7b4f27401e9421`

Foundry `1.9.0`, compiler `0.8.19+commit.7dd6d404`. Candidate settings are **not exhaustive**:

| Candidate from originally pinned source | Build | Historical executable bytecode |
|---|---|---|
| via-IR, optimizer 200 | PASS | MISMATCH |
| via-IR, optimizer 1,000 | PASS | MISMATCH |
| via-IR, optimizer 10,000 | PASS | MISMATCH |
| legacy non-via-IR, optimizer 200 | PASS | MISMATCH |

The earlier pinned source's `package.json` uses `forge build --via-ir`, but the published repository `foundry.toml` alone does not prove historical production compiler flags.

Additional alternative historical source commits independently built under legacy and via-IR, both optimizer 200:

| Historical source commit | Legacy optimizer 200 | Via-IR optimizer 200 |
|---|---|---|
| `1faac76f50db861331905391cb95b55d278391d9` | **EXECUTABLE PREFIX MATCH** | MISMATCH |
| `eb2b6278d322f97f387869db56093f30e44b15c8` | MISMATCH | MISMATCH |
| `2ea68bd9b9da3c77debc135a6df76cc42fe89c60` | MISMATCH | MISMATCH |
| `7737f27062d5eaea5ada56efc22ee9264be62d95` | MISMATCH | MISMATCH |

These are revision hypotheses, not a search of all historical versions/optimizer parameters.

### Exact executable match: numeric evidence

At each tested historical calculator snapshot:

| Quantity | Historical `1faac76f` legacy build | Base deployed |
|---|---|---|
| Full runtime bytes | 12,448 | 12,448 |
| Recognized CBOR metadata bytes | 51 (+2 footer) | 51 (+2 footer) |
| Executable prefix bytes | **12,395** | **12,395** |
| First differing byte index (0-based) | 12,405 | 12,405 |
| First executable-prefix difference | **NONE** | **NONE** |
| Keccak-256 of *full* runtime | `0xf7de940a943243fde1aad0854840dfb8f15559fa24ba24f37bcf7838827b22a4` | `0x18a0f3dc9ce66d94741ad4e13edf136a497154f96c828bfa9148bc0591a1900b` |

This is a strong match for **executable Solidity runtime** and a clear **nonmatch in metadata**. The CBOR tail is not blindly truncated: the audit verifies the Solidity metadata length footer and CBOR-map envelope before executable comparison. It does not assert equivalence of provenance embedded in the different metadata hashes, nor assume the compiled metadata was part of deployment.

The historical candidate [source commit 1faac76f](https://github.com/ToucanProtocol/dynamic-fee-pools/tree/1faac76f50db861331905391cb95b55d278391d9) retrieves TCO2 `getVintageData().projectTokenId` and uses a project-ID inventory method. This aligns with actual call traces in Gate 25, unlike the later pinned source's `totalPerProjectSupply(address)` ABI. The code and byte-comparison evidence are stronger than the superficial ABI similarity alone.

## Historical snapshots and proxy-version boundary

The audit uses independent JSON-RPC `eth_getCode`, `eth_getStorageAt` (ERC-1967 implementation), and pool `feeCalculator()` calls at **end-of-block snapshots**. These snapshots are *not* represented as exact intra-block prestates; the Gate 25 transaction-hash fork separately provides exact prestates at the two receipt transactions.

| Base block | Active pool implementation | FeeCalculator runtime hash |
|---:|---|---|
| 13,826,400 (deposit B−1) | `0xb61763cf40e53df924856925461d5914c274ecd8` | `0x18a0f3…1900b` |
| 13,826,401 (deposit B) | same | same |
| 15,709,580 (redemption B−1) | same | same |
| 15,709,581 (redemption B) | same | same |
| 58,258,072 (later checkpoint) | `0x23da31aa73720f770c21e9ec0a8382ec279e0c85` | same |

- Earlier pool implementation full runtime hash: `0x9e01a24f7396330a59b37961a59c3ea2db412674f62570fdbb29bb0c73204c80`
- Later checkpoint pool implementation hash: `0xf21ea35f49a2c39a3b97833fcb82c0526da68a85fa00b98cec09516f478f397b`
- Historical FeeCalculator address is the same at all five snapshots, and its runtime hash is constant at those snapshots.

The calculator and pool implementation are **different contracts**. The pool proxy's implementation changed at some point between the early and later checkpoints; these five snapshots do **not** date or enumerate all proxy upgrades. **No pool-implementation source-to-deployed equivalence was established** by this Gate 26 calculation-focused source search.

The two B-block FeeCalculator/pool-implementation codehashes exactly match the **pre-transaction EVM codehash anchors** from Gate 25. This permits using the same calculator executable at those actual transactions without pretending end-of-block state equals pre-transaction inventory.

## Research relevance and restrictions

1. Gate 25's **actual fee reproduction** remains valid independently of the original GitHub source match. It invoked the active deployed module on a fork immediately before each transaction and compared each quoted fee recipient with independent raw receipts.
2. For formal model primitives, quote the **historically deployed parameter vector** from Gate 25, not the newer source defaults: deposit scale 0.15; deposit ratio scale 1.25; redemption scale 0.30; shift 0.10. These values are historical **storage**, not compiler settings.
3. The published `7aef954d` source **must not** be represented as bytecode-identical to the historical deployed calculator. The historical `1faac76f` candidate is the better source for executable fee logic in the studied receipts.
4. Full metadata matching requires original exact Standard JSON compilation input, source paths/settings and compiler metadata evidence or verified-source build records. Executable-prefix matching does not identify the exact deployed metadata.
5. Nothing here establishes all transaction coverage, all pool execution branches, producer wallet ownership, commercial pass-through `beta`, cash financing, additional removal, or blockchain superiority versus a conventional platform.
6. Public deployment documentation and a source verification claim are useful external corroboration, but this repository's independent result is **executable-prefix matching**, not a self-certified byte-for-byte verification.

## Gate decision

**Gate 26: PARTIALLY CLOSED — scoped FeeCalculator executable equivalence established for the historical revision `1faac76f` at declared snapshots; originally pinned later revision NOT matched under tested configs; full runtime metadata identity and pool implementation provenance remain OPEN.**

To close the rest without overclaiming: retrieve the verified original Standard JSON input for the historical FeeCalculator and reproduce the exact CBOR metadata/hash; verify the active Pool proxy implementation source at each relevant historical transaction; enumerate upgrades and version-specific execution rules only if this additional scope is necessary for research questions. Do not delay the conditional economic equilibrium analysis on unrelated network-wide attribution.
