# Biochar ReFi — smart-contract economic mechanism research

**This working tree is intentionally separated from the previous Paper-2
N-H / S-H / F-H perishable-food simulation.**

It contains **only** the Toucan CHAR protocol source validation and
deployment-state audit. The earlier SCM project remains unchanged on `main`.

## Research boundary

- Setting: biochar carbon removal supply chain and tokenized CORCs.
- Core question: how programmable fee, execution and allocation rules shape
  intermediary decisions, liquidity, project representation and value
  transmission in a supply chain.
- **No claim** of blockchain superiority.
- **No verified producer-royalty amounts, beta, additional biochar output,
  or marginal carbon removal** currently.
- EVM source tests are distinct from historical Base mainnet deployment proofs.

## Run

```bash
git clone --branch research/char-refi-standalone \
  https://github.com/plinhnguyende-svg/Paper-2-model0.git
cd Paper-2-model0
mkdir -p lib
git clone https://github.com/ToucanProtocol/dynamic-fee-pools.git lib/dynamic-fee-pools
git -C lib/dynamic-fee-pools checkout --detach 7aef954dae1bd0c7add4ed66d216251110521b16
git clone --depth 1 --branch v4.9.6 https://github.com/OpenZeppelin/openzeppelin-contracts.git lib/openzeppelin-contracts
git clone --depth 1 --branch v4.0.3 https://github.com/PaulRBerg/prb-math.git lib/prb-math
forge test -vvvv
```

GitHub Actions automatically runs `forge test` on pushes to this clean branch.
For current Base state, the optional script reads all views at one block.
For historical EVM matching, choose the historical block and use an archive
RPC. Never apply current values retrospectively.

## Data policy

See [data/README.md](data/README.md). Synthetic analyses are separated
from on-chain observations; no generated transaction history is presented as
empirical data.

## Migration to a truly separate repository

Recommended new repository name: `biochar-refi-smart-contract-design`.
Create an empty GitHub repository, clone this clean branch, then push its
contents as the new default main. **Do not merge into the old Paper-2 main.**
Git history remains shared until a truly independent repository is created.
