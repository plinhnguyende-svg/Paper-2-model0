# Research data and project isolation

**Old Paper 2:** N-H / S-H / F-H, perishable exporters to importer and retailers.
This code is kept on the existing `main` branch.

**New Paper 2 Track C1:** Toucan CHAR, biochar CORCs, dynamic deposit / redemption
fee rules, maxFee execution, fee-recipient allocation, and intermediaries.

Never join the two datasets, scenario IDs, or outputs. The actors and state
variables are not interchangeable.

Version claim hierarchy:
1. Source-level mathematical formula.
2. Foundry EVM execution of *pinned upstream source*.
3. Same-block mainnet proxy and calculator state.
4. Historical transaction/implementation matching at block B.
5. Independently attributed recipient payments.
6. Producer income and physical output outcomes.

Stages 3-6 are **UNVERIFIED** unless logs or primary contracts prove them.
FeeSetup shares are not automatically producer pass-through beta.
