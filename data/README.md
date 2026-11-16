# Data provenance rules

- `raw_onchain/`: unmodified RPC/Dune blockchain extracts, chain, block, tx hash, source URI.
- `processed/`: decoded events with script commit and schema.
- `synthetic/`: synthetic model outputs only, filename must contain SYNTHETIC.
- `external/`: registry data with attribution and access timestamp.
- `logs/`: Foundry and CI execution proof.

No binary datasets or live secrets committed. Do not infer zero transactions
from missing data or call a test fixture an observed market event.
Historical fee reconstruction must use matching chain/block/proxy version.
