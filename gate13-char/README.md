# Gate 13 – Toucan CHAR contract-source and deployment audit

Isolated research branch; does not alter the existing supply-chain Paper 2 model on main.

## What CI can validate

1. **Source-level Foundry tests** against a pinned Toucan FeeCalculator revision.
2. **EVM 18-decimal behavior** near the single-project boundary, including reverts.
3. **Current-block Base state inspection** if an RPC is reachable (separate from tests).
4. The original 2024 `FeeSetup` transaction/receipt can be saved when RPC supports it.

These are different evidentiary claims. Passing source tests does **not** prove
the Base CHAR proxy used the same implementation in 2024 or 2026.

## Run

```bash
cd gate13-char
# clone dependencies at the revisions listed in the GitHub workflow
forge test --match-path test/SourceCHARBoundary.t.sol -vvvv
```

### No secrets required for source tests

For optional Base verification, configure the GitHub Actions repository secret
`BASE_RPC_URL` with a trusted archive-capable Base endpoint.
If omitted, the workflow attempts public https://mainnet.base.org
and explicitly records UNVERIFIED if state calls fail.

## Addresses

- Base CHAR proxy: 0x20b048fA035D5763685D695e66aDF62c5D9F5055
- Base FeeCalculator artifact: 0x6A4549759C475d845d4AE074B3656dC257490DA5

Current block state is **not** a substitute for historical state. To match a
specific transaction, query proxy implementation, fee module, parameters,
filter, recipients, and transaction receipt at the SAME block.

## Institutional caution

Puro's CO2 Removal Supplier can be the producer OR a contracted representative.
A fee-recipient wallet is not evidence of a producer payment without validated
attribution and off-chain commercial arrangements.
