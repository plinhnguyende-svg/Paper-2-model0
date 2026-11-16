#!/usr/bin/env bash
# Historical EVM checkpoints for Toucan CHAR / Base (chain 8453).
# Does NOT claim EVM matching until all calls succeed and bytecode is verified.
set -euo pipefail
OUT="${1:-history}"
mkdir -p "$OUT/receipts"
RPC="${BASE_RPC_URL:-https://mainnet.base.org}"
echo 'Chain: Base 8453' > "$OUT/SCOPE.txt"
echo 'Explorer-indexed upgrades (NOT independently receipt decoded):' >> "$OUT/SCOPE.txt"
echo '2024-04-17 09:02:51 UTC at block 13277612 -> implementation 0xb61763Cf40e53Df924856925461d5914c274ecD8' >> "$OUT/SCOPE.txt"
echo '2025-03-31 12:21:57 UTC at block 28317185 -> implementation 0x23Da31aa...C279e0C85 (full address must be read from storage)' >> "$OUT/SCOPE.txt"
echo 'Block B returns END-OF-BLOCK state; use execution traces for exact within-block prestate.' >> "$OUT/SCOPE.txt"
echo 'An archive-capable RPC is needed for historical eth_getStorageAt / eth_call.' >> "$OUT/SCOPE.txt"
for B in 13277611 13277612 28317184 28317185; do
  echo "Reading at block $B"
  BASE_BLOCK_NUMBER="$B" BASE_RPC_URL="$RPC" bash scripts/snapshot_base.sh "$OUT/block_$B"
done
receipt(){
  local label="$1" tx="$2"
  if cast receipt "$tx" --json --rpc-url "$RPC" > "$OUT/receipts/$label.json" 2>"$OUT/receipts/$label.error"; then
    echo "$label RECEIPT_OK" >> "$OUT/SCOPE.txt"
  else
    echo "$label RECEIPT_UNVERIFIED" >> "$OUT/SCOPE.txt"
  fi
}
receipt upgrade_2024 0x82be42a17af9fab33b9d4391e8b82e3d246c4f60783ea8eeb2fa5ba0b5ffd415
receipt upgrade_2025 0xf6035600a29a265efe4519c0b2d0faa423c6b3f49532ab0ab0f3222ce6e848d7
receipt feesetup_2024 0x1e4187be16964075654028ea7c92c02fc798d4bb097cab53efb5847cd85c91c0
printf '\nVALIDATION REMAINS OPEN until:\n* source bytecode compared with actual implementation bytecode,\n* active fee calculator and parameters matched at desired transaction pre-state,\n* FeeSetup and Transfer receipts decoded and reconciled,\n* historical token/project inventory reconstructed.\n' >> "$OUT/SCOPE.txt"
