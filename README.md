# Biochar ReFi — smart-contract economic mechanism research

## Current research entry points (Gate 21)

- [Topic, smart-contract role and full RQ/proof map (Vietnamese)](docs/GATE21_RESEARCH_MAP_VI.md)
- [Deposit-scale designer and scoped proofs](docs/GATE21_DESIGNER_PROOFS.md)
- [Gate 21 results](docs/GATE21_RESULTS.md)
- [Partial-pooling baseline](docs/GATE20_PARTIAL_POOLING_PROOFS.md)
- [Machine-readable scope](config/research_scope.json)

The default economic baseline allows partial venue allocation. Gate 19's lower-output
result is a conditional all-output contrast, not a general pooling claim.
The current designer chooses a source-permitted depositFeeScale from a finite menu;
commercial beta and pre-production finance are separate assumed contracts/constraints.
No functional optimal mechanism, governance equilibrium or verified producer financing
is established. Offline economic checks and historical transaction evidence have
separate CI status.


**This working tree is intentionally separated from the previous Paper-2
N-H / S-H / F-H perishable-food simulation.**

It contains the CHAR economic models, source/deployment audit and reproducible
synthetic design experiments. The earlier SCM project remains unchanged on `main`.

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
git clone --branch research/char-evm-verification-pr \
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
