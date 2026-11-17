# Gate 27 — verified deployment provenance and conditional continuous-fee equilibrium

Date: 2026-11-17. Draft PR #21; branch `research/char-evm-verification-pr` → `research/char-refi-standalone`. Do not merge to legacy main.

## Executive verdict (distinct levels)

**Technical source-to-deployment equivalence: CLOSED FOR THREE SPECIFIC HISTORICAL CONTRACT RUNTIMES.**

1. Retrieved original verified **Solidity Standard JSON inputs and outputs** through Sourcify v2 for (i) FeeCalculator, (ii) early Biochar pool implementation, (iii) later Biochar pool implementation.
2. Independently compiled the original inputs with Solidity **0.8.19** for FeeCalculator, and **0.8.14-fixed** for Biochar implementations; the latter is the working npm wrapper for genuine Solidity 0.8.14+commit.80d49f37.
3. Recreated the **full runtime bytecode including Solidity CBOR metadata** of FeeCalculator. Recreated the full on-chain runtime bytecode of both Biochar implementations after inserting immutable values at verified positions (constructor-assigned immutables, not arbitrary metadata stripping).
4. Compared this exact runtime against independent historical Base `eth_getCode` responses at declared blocks. All **three contracts matched byte-for-byte**. The on-chain hashes additionally align with Gate 25–26 EVM evidence.
5. Located one specific Biochar **proxy implementation upgrade** at Base block 28,317,185 and the actual `Upgraded(address)` event. This is **not** an exhaustive scan of all historical upgrades.
6. In parallel, derived and tested an analytical inverse relation between an interior, unsaturated production equilibrium `y` and the continuous smart-contract fee scale `a`. This is a **conditional partial equilibrium**, not a globally optimal continuous fee mechanism or an observed physical CDR effect.

**Canonical technical and mathematical CI:** [Gate 27 run 44027871448](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/runs/44027871448), commit `394801bbb990654bcda17ba6725507b8e40a5072`, two independent jobs SUCCESS (provenance and mathematical tests). Exact raw evidence: [verified builds and proxy history artifact](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/runs/44027871448/artifacts/14302994523) and [conditional mathematical model artifact](https://github.com/plinhnguyende-svg/Paper-2-model0/actions/runs/44027871448/artifacts/14303642438).

## A. Historical source and exact reproducibility

### Original public verification source

Sourcify v2 read-only endpoints:

- FeeCalculator: `https://sourcify.dev/server/v2/contract/8453/0x6A4549759C475d845d4AE074B3656dC257490DA5?fields=all`
- Old Biochar implementation: `https://sourcify.dev/server/v2/contract/8453/0xb61763cf40e53df924856925461d5914c274ecD8?fields=all`
- New Biochar implementation: `https://sourcify.dev/server/v2/contract/8453/0x23da31aa73720f770c21e9ec0a8382ec279e0c85?fields=all`

Each reports `match=exact_match`, `creationMatch=exact_match`, and `runtimeMatch=exact_match`, and contains compiler settings, `stdJsonInput` (original sources/settings), `stdJsonOutput`, CBOR metadata and deployed bytecode.

| Target | Source fully qualified name | Solidity compiler | Optimizer | EVM version | Metadata | Full deployed runtime | Independently reproduced |
|---|---|---|---|---|---|---:|---|
| FeeCalculator | `@toucanprotocol/dynamic-fee-pools/src/FeeCalculator.sol:FeeCalculator` | `0.8.19+commit.7dd6d404` | 200 runs | Paris | IPFS + literal content | 12,448 bytes | **EXACT** |
| Early pool impl | `contracts/pools/Biochar.sol:Biochar` | `0.8.14+commit.80d49f37` | 200 runs | London | IPFS + literal content | 20,694 bytes | **EXACT after immutable substitution** |
| Later pool impl | `contracts/pools/Biochar.sol:Biochar` | `0.8.14+commit.80d49f37` | 200 runs | London | IPFS + literal content | 22,332 bytes | **EXACT after immutable substitution** |

Independent compiler procedure:

- `solc@0.8.19` npm package for calculator; `solc@0.8.14-fixed` for both Biochar sources. The original `0.8.14` npm wrapper is known to lack `./common/helpers`; `0.8.14-fixed` retains the same official compiler version.
- The input is the actual public `stdJsonInput`, not a reconstructed guess from code snippets. An `outputSelection` field is added solely to request the runtime and metadata; no contract source or material compiler setting is changed.
- The newly compiled runtime is first compared to the Sourcify `recompiledBytecode`. For the two proxy implementations, compilation-provided immutable references and verified creation-derived values are applied; the fully patched bytes are compared with `onchainBytecode`.
- The three public `onchainBytecode` blobs were independently compared to real Base historical `eth_getCode` for FeeCalculator and the early implementation at block 13,826,401, and the later implementation at block 58,258,072. All match exactly. `SHA256` values below provide independently reproducible archive fingerprints, **not** contract address identities.

| Target | Independently reproduced final-runtime SHA-256 |
|---|---|
| FeeCalculator | `f252adbd33a252668fb2b4d6c4dc23b0c8dbf874b0b846475076db5bb624a8ec` |
| Old Biochar | `ef90a89ec0404172bc4649f260e5f0f25ad199d4cef81007dfd0e8c3a3352c1f` |
| New Biochar | `5ee9c96f2c255db2a45f367e264f5fa8e86c77d3187c19f55ab94fc95c18e301` |

For both Biochar builds, serialized `immutableReferences` descriptions are not identical to the public response's representation; **full runtime after immutable application is byte-for-byte equal regardless**. This difference is retained in the machine-readable `*_INDEPENDENT_REBUILD.json` files, not hidden.

### Reinterpretation of Gate 26

The later published source revision `7aef954dae1bd0c7add4ed66d216251110521b16` did not produce deployed executable code under its declared tested configurations (Gate 26). Historical source commit `1faac76f50db861331905391cb95b55d278391d9` independently reproduced the same executable prefix but not CBOR. Gate 27 **does not reverse these results**: it recovers the historical *actual compilation inputs*, source path layout, compiler version/settings and literal content from the verified build, which is the appropriate evidence for exact historical deployment provenance. The older public git commit is a helpful provenance witness but should not be substituted for the verified standard input.

All independent evidence is version- and historical-block-specific. It does not establish that current owner-controlled parameters, pool upgrades or token incentives have remained constant over every unexamined period.

## B. Pool implementation change and bounded upgrade record

The proxy is `0x20b048fa035d5763685d695e66adf62c5d9f5055`.

- Old implementation: `0xb61763cf40e53df924856925461d5914c274ecd8`; active at Gate 25 deposit and redemption transactions, and the old checkpoint.
- New implementation: `0x23da31aa73720f770c21e9ec0a8382ec279e0c85`; active at later Base block 58,258,072.
- Historical EIP-1967 storage search between known different endpoints localizes the **observed change boundary to block 28,317,185**. At block 28,317,184 the slot holds the old implementation; at block 28,317,185 the slot holds the new implementation.
- An actual `Upgraded(address)` event at block 28,317,185, pool contract address, log index 118, points to the new implementation. Transaction: `0xf6035600a29a265efe4519c0b2d0faa423c6b3f49532ab0ab0f3222ce6e848d7`.
- Sourcify's verified build records show creation transactions for each implementation and original compiler/metadata evidence; this is distinct from the proxy upgrade transaction.

**Scope restriction:** binary search of the implementation storage slot assumes the observed change can be localized between two different endpoint values. The confirmed event is strong evidence of this **one transition**, not a census of all historical `Upgraded` logs. Other earlier/later upgrades or intermediate reversion cannot be excluded by this result alone. Current/historical governance privileges still require a separate institutional audit.

## C. A genuinely conditional economic equilibrium beyond the 30-scale menu

### Agents, time and economic primitives

Public initial project inventory `q`, pool total `Q>q`, verified credit yield `eta>0`. A one-horizon designer selects scale `a` before production. Producer selects `y>=0`, incurs `cy + k y^2/2` with `k>0` and early cash limit. Intermediary can pool `z in [0,eta*y]` and sell the remainder outside; no mandatory all-output routing. The outside price `v`, CHAR value `P>v`, minimum producer procurement price `b0`, fixed gas `g>0`, and commercial pass-through `beta in (0,1)` are modeled assumptions. `beta` **is not** the on-chain fee-recipient share and has not been identified empirically.

For a fixed multi-project state, the real source-formula deposit cost is `F_a(z)=a*f(z)` with

```math
f(z)=q log10(1-r*q/Q)
     -(q+z) log10(1-r*(q+z)/(Q+z)).
```

The Gate 19–20 proofs establish `f'(z)>0`, `f''(z)>0` on the real log domain. The intermediary's incremental net pooling surplus is

```math
S_a(z)=(P-v)*z-P*a*f(z)-g.
```

Under intermediary participation, `z` maximizes gross pooling gain subject to available credits. Producer's payoff is

```math
U_a(y)=(eta*b0-c)*y - k*y^2/2
       + beta*max(0, max_{0<=z<=eta*y}[(P-v)*z-P*a*f(z)]-g).
```

This is a complete reduced producer–intermediary partial-equilibrium decision under the contract and price assumptions, not a jointly determined credit-market price equilibrium or Bayesian mechanism.

### Gate 27 result: inverse equilibrium fee scale

Let `y0` be the outside-only optimal output, strictly below the early-cash bound. For an **interior, selected, strictly expanded, unsaturated** active equilibrium, pooling uses `z=eta*y`, so the producer FOC is

```math
eta*b0-c-k*y+beta*eta*((P-v)-P*a*f'(eta*y))=0.
```

Solving for the actual policy control `a` gives the **exact inverse mapping**

```math
a(y)=[eta*b0-c+beta*eta*(P-v)-k*y]
     /[beta*eta*P*f'(eta*y)].
```

Let `N(y)=eta*b0-c+beta*eta*(P-v)-k*y`. Whenever `N>0`, `f'>0`, `f''>0` and all domain guards hold,

```math
a'(y)=(-k*f'(eta*y)-N(y)*eta*f''(eta*y))
      /[beta*eta*P*(f'(eta*y))^2] < 0.
```

**Proof:** `N'(y)=-k`; apply the quotient rule to `a(y)=N(y)/[beta eta P f'(eta y)]`. Both numerator terms are strictly negative, and the denominator is positive. Thus higher interior equilibrium output requires a lower positive scale within the specified response regime. This is NOT a statement about every possible endogenous routing/policy corner.

**Global-selection checks:** a value reconstructed from the FOC is only a **candidate**, not automatically an equilibrium. Gate 27 independently verifies all of the following: `a in (0,1]`, gas-inclusive intermediary surplus positive, `0<F_a(eta y)<eta y`, active producer global value strictly greater than outside benchmark, `z=eta y` optimal without saturation, no pre-production cash binding, log domain, and exact agreement with Gate 20's globally reduced producer/routing response. The designer must also verify after-deposit HHI and minimum **token fee** budget. These recipient fee tokens do not prove producer income.

### A useful continuous-design reduction, without false existence claims

Any strict expansion `y>y0` that is interior and unsaturated has a unique candidate scale `a(y)`; hence the designer can equivalently search feasible output `y` instead of continuously searching over fee scale `a`. The feasible output set must satisfy simultaneously:

1. `0<a(y)<=1`, log and exact-action domain, slack early cash;
2. `S_{a(y)}(eta*y)>0` and active-producer value above the outside maximum;
3. the inventory-concentration limit `H_after(eta*y)<=H_bar`;
4. the token-fee budget `a(y)*f(eta*y)>=B`.

The latter is **not assumed monotone** in `y`: although `a(y)` falls and `f(eta y)` rises, their product can vary nonmonotonically. Therefore a bisection root around one fee-budget crossing proves only a local boundary. Existence and global optimality of a continuously chosen fee scale across all regimes and discontinuous participation thresholds remain OPEN. The outside-only and saturation/cash-bound branches remain part of the global design problem.

### Synthetic numerical certificate (no mainnet behavioral data)

Scenario: `Q=100, q=10, eta=P=1, v=.55, b0=.5, beta=.25, c=.15, k=.01, gas=.1`, unbounded liquidity, real formula ratio `r=1.25`. This value of `r` was historically observed in the deployed calculator, **but the quantities/prices/beta are hypothetical**.

- Outside-only production: `y0=35`.
- At continuous fee scale `a=.05`, Gate 20 global solution `y*=45.5914031569`, `z*=45.5914031569`. The analytically inverted `a(y*)` equals .05 to numerical precision.
- Fee `F=0.7541168143` in modeled units; modeled pooling surplus after gas `S=19.6620146063`; producer active payoff `10.4796145474` vs outside `6.125`. HHI is `0.5279275261` vs the stipulated upper bound `0.84`. These are synthetic values, not producer transaction receipts or actual carbon credits removed.
- For a stipulated fee-token budget `B=.5`, the local budget crossing between `a=.03` and `a=.04` is approximately **`a=0.03289369150`**, giving **`y=45.8152651492`**. This numerical crossing is a *candidate for continuous design*, **NOT A PROVEN GLOBAL CONTINUOUS OPTIMUM**.

Seven unit tests confirm the inversion against the independent Gate 20 response, strict comparative statics in the interior, and rejection of incompatible corner regimes. Additional preexisting Gates 19–21 are unaffected.

## D. Evidentiary and publication implications

- The previously unresolved exact historical compiler provenance can now be described as **independently reproducible** for the three selected deployed contracts and historical states. Preserve raw Standard JSON inputs, exact runtime equality, immutable patch data and historical block snapshots as an artifact.
- For pricing architecture, use verified deployed historical fee configuration `depositFeeScale=0.15`, `depositFeeRatioScale=1.25`, `redemptionFeeScale=0.30`, `redemptionFeeShift=0.10` observed in Gate 25. The synthetic continuous scale experiment deliberately varies the control away from .15; it is **counterfactual**, not a realized owner choice.
- This audit does not prove that the actual producer received a share of fee tokens. The `beta` cash pass-through contract, token price realization, producer finance, carbon additionality and social welfare effects remain unidentified.
- A capable conventional marketplace can also use the same fee formula. A technology-specific contribution requires a separate comparison of governance/commitment, observability, execution cost or multilateral rights. Do not conflate successful smart contract reproduction with a blockchain superiority theorem.
- A complete whole-history pool upgrade/event census is separate from the one boundary and upgrade transaction documented here.

**Gate 27 decision:** technical verified source-to-deployment matching for these three artifacts **PASS**; one historical proxy transition confirmed but complete upgrade census **OPEN**; conditional continuous fee/output inversion theorem and one model certificate **PASS**, global continuous mechanism optimum and empirical causal claims **OPEN**.
