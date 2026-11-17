# Gate 23 — RPC access preflight and staged transaction evidence

17 November 2026. No empirical claim is upgraded by this infrastructure change.

## Observed blocker

Failed-only rerun of Actions run 44015841627, data job 133816115625, exposes an
empty BASE_RPC_URL environment variable and produces zero matched receipts.
This establishes no credential was available to that job; it does not inspect
repository secret metadata or prove absence at every scope.

## Access activation

Open https://github.com/plinhnguyende-svg/Paper-2-model0/settings/secrets/actions
and create repository Actions secret BASE_RPC_URL using your authorized Base RPC.
Required: historical eth_getLogs, transaction/receipt/block reads and historical
eth_getCode/eth_getStorageAt. A signing key is neither needed nor requested.
The connected GitHub tools do not expose Actions-secret administration. No provider
account or private endpoint was supplied, so this step remains user-dependent.
Never paste the URL or token into the conversation, source, PR or issue.

The new preflight records only credential presence and sanitized failure type.
It validates chain 8453, known successful FeeSetup transaction and canonical
block membership, exact receipt-versus-getLogs event consistency at block
13197311, historical pool code and ERC-1967 slot at block 58258072. It does not
infer source-bytecode equivalence or guarantee all blocks/methods are accessible.
Raw successful responses and hashes are archived. A missing secret exits 2;
a failed capability assertion exits 1. Neither is reported as empirical success.

## Four separate acceptance levels

| Level | Evidence required | Current status |
|---|---|---|
| Receipt accounting | Successful canonical tx, fee events and underlying/CHAR flows reconcile | OPEN; existing bounded collector follows preflight |
| Exact fee reproduction | Pre-transaction inventory/configuration, active implementation and exact EVM fee reproduce receipt | OPEN; block-minus-one alone is insufficient if earlier txs change state in same block |
| Coverage | Declared chain/address/time universe, complete pagination/chunk ledger, failed intervals and exclusions | OPEN; bounded receipt samples are explicitly nonrepresentative |
| Beneficiary attribution | Independent dated evidence of wallet control and relevant commercial rights | OPEN; fee shares are not contractual beta |

After adding the secret, rerun failed jobs for the current PR workflow. A preflight
PASS means the known access sample passed; the following collector must still
obtain actual matched receipts. Save successful artifacts before creating an offline
replay dataset. Full historical replay requires transaction-index-aware execution
or an equivalent validated reconstruction; no producer financing inference follows
from token receipts alone.

Theoretical RQ2-to-RQ3 results remain conditional on commercial pass-through,
outside access and liquidity. These access/decoder checks are validation support,
not separate economic contributions or novelty evidence.
