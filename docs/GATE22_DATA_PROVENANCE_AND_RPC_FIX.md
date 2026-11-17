# Data provenance and transaction-collection repair

## Honest classification of the current paper

The study is an analytical economic-design paper grounded in an actual protocol's
published source and selected historical deployment observations, with SYNTHETIC
economic experiments. It is not yet an empirical causal study or a fully data-
calibrated production/market model.

| Input or result | Origin | What it supports |
|---|---|---|
| Fee formulas, branches, administrative setters and allocation paths | Pinned published code | Specification and executable-rule motivation |
| Historical implementation/calculator/fee parameters and FeeSetup receipt | Prior archived RPC/checkpoint evidence | Selected actual contract states, not an uninterrupted history |
| Website-indexed seven-project inventory snapshot | External page snapshot, not block pinned | Illustrative initialization only |
| Prices, costs, beta, gas assumptions and hypothetical producers | Assumed synthetic model inputs | Conditional comparative statics and policy experiments |
| HHI slack .02, budget .5, approved menu | Declared normative design inputs | Finite-menu design exercise, not estimated owner preferences |
| Producer output and optimized policies | Derived/simulated outputs | No actual production or financing measurement |
| Whole-pool fee-bearing transactions | New bounded collector, if successful | Receipt accounting sample, not causal effect or full calibration |

## Diagnosed error and repair

Artifact 14297596954 from run 44013087005 confirms eth_getLogs failed with HTTP
429, RPC -32011, request limit reached. This is a data-access error, not a failed
economic theorem or a failed source/fork assertion. The former collector used the
same Base public endpoint repeatedly across later runs.

The repaired pipeline:
1. Verifies Base chain ID for each usable RPC and records provider per receipt.
2. Supports a configured RPC plus PublicNode and Base public fallbacks; failures
   are method-specific and sanitized, not concealed as empty activity.
3. Uses at most four Blockscout token-transfer pages to nominate mint/burn txs;
   the indexer is discovery only. RPC transaction/receipt/block identities must match.
4. If indexer discovery is unavailable, scans the declared recent historical window
   in bounded chunks with RPC method failover. No full-history claim is made.
5. Decodes known pool events and checks them against actual ERC20 mint/burn/
   transfers and underlying movements. Synthetic fixtures are separately labeled.
6. Attempts call/prestate tracing for the first matched receipt, retaining failures.
7. Saves raw evidence, actual matched receipt rows, failure ledger and SHA256 manifest.

The data collection is now a separate job from source/fork verification. It still
fails if no actual fee-bearing receipt passes the narrow accounting checks. No
continue-on-error or replacement of missing chain data with synthetic results is used.

## Exact meaning of a passing new sample job

RECEIPT_SAMPLE_ACCOUNTING_PASS_FULL_RECONCILIATION_OPEN means at least one actual
successful canonical transaction has matching event/token-flow accounting under
the narrow decoder. It does NOT mean exact prestate fee reproduction, bytecode
equivalence, project ID history, recipient identity or producer financing is solved.
Mixed/multi-call/self-recipient patterns may be labeled unsupported or ambiguous
rather than forced into a simple accounting identity. The explicit full-reconciliation
field remains OPEN until a separate formula/state/execution comparison is performed.

Provider references checked in this session: https://base.publicnode.com/ and
https://base-rpc.publicnode.com; discovery endpoint schema from the official
Blockscout API documentation/source, using the Base explorer at
https://base.blockscout.com/. No wallet credentials or transaction broadcasts are used.

## Implications for calibration and contribution

A small verified receipt sample can ground token-level financial flow and illustrate
rules actually used. It cannot estimate participation elasticities, producer beta,
working capital or new biochar output. Larger transaction panels, market prices,
legal/contract records and producer data would be needed for those empirical claims.
Until then describe results as institutionally grounded theory and sensitivity
analysis, and keep the RQ2-to-RQ3 transmission theorem explicitly conditional.
