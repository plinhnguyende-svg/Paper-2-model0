#!/usr/bin/env bash
# Audits one coherent Base block, NOT a historical proxy/implementation proof.
set -euo pipefail
POOL=0x20b048fA035D5763685D695e66aDF62c5D9F5055
CALC_ARTIFACT=0x6A4549759C475d845d4AE074B3656dC257490DA5
SLOT=0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc
FEESETUP_TX=0x1e4187be16964075654028ea7c92c02fc798d4bb097cab53efb5847cd85c91c0
OUT="${1:-gate13-char/block_state}"
mkdir -p "$OUT"
RPC="${BASE_RPC_URL:-https://mainnet.base.org}"
if ! BLOCK=$(cast block-number --rpc-url "$RPC" 2>"$OUT/rpc_error.txt"); then
  echo "UNVERIFIED: Base RPC unavailable" | tee "$OUT/STATUS.txt"
  exit 0
fi
echo "Base block: $BLOCK" | tee "$OUT/STATUS.txt"
echo "Same-block data; no proof that public GitHub source matches proxy bytecode." >> "$OUT/STATUS.txt"
printf '%s\n' "$BLOCK" > "$OUT/block.txt"
query() {
  local label="$1"; shift
  if "$@" > "$OUT/$label.txt" 2> "$OUT/$label.error.txt"; then
    echo "$label: OK" >> "$OUT/STATUS.txt"
  else
    echo "$label: CALL_FAILED" >> "$OUT/STATUS.txt"
  fi
}
query proxy_implementation_slot cast storage "$POOL" "$SLOT" --block "$BLOCK" --rpc-url "$RPC"
query pool_version cast call "$POOL" 'VERSION()(string)' --block "$BLOCK" --rpc-url "$RPC"
query pool_fee_calculator cast call "$POOL" 'feeCalculator()(address)' --block "$BLOCK" --rpc-url "$RPC"
query pool_total_underlying cast call "$POOL" 'totalUnderlyingSupply()(uint256)' --block "$BLOCK" --rpc-url "$RPC"
query pool_filter cast call "$POOL" 'filter()(address)' --block "$BLOCK" --rpc-url "$RPC"
query pool_owner cast call "$POOL" 'owner()(address)' --block "$BLOCK" --rpc-url "$RPC"
query pool_paused cast call "$POOL" 'paused()(bool)' --block "$BLOCK" --rpc-url "$RPC"
query pool_seeding_threshold cast call "$POOL" 'minimumTCLSeedingThreshold()(uint256)' --block "$BLOCK" --rpc-url "$RPC"
query pool_supply_cap cast call "$POOL" 'supplyCap()(uint256)' --block "$BLOCK" --rpc-url "$RPC"
FEE="$CALC_ARTIFACT"
if [[ -s "$OUT/pool_fee_calculator.txt" ]]; then
  CANDIDATE=$(sed -n 's/^\(0x[0-9a-fA-F]\{40\}\).*$/\1/p' "$OUT/pool_fee_calculator.txt" | head -1)
  if [[ -n "$CANDIDATE" && "$CANDIDATE" != 0x0000000000000000000000000000000000000000 ]]; then
    FEE="$CANDIDATE"
  fi
fi
printf '%s\n' "$FEE" > "$OUT/active_fee_calculator_address.txt"
query calculator_version cast call "$FEE" 'VERSION()(string)' --block "$BLOCK" --rpc-url "$RPC"
query fee_setup cast call "$FEE" 'getFeeSetup()(address[],uint256[])' --block "$BLOCK" --rpc-url "$RPC"
query calculator_owner cast call "$FEE" 'owner()(address)' --block "$BLOCK" --rpc-url "$RPC"
for sig in depositFeeScale depositFeeRatioScale redemptionFeeScale redemptionFeeShift singleAssetDepositRelativeFee singleAssetRedemptionRelativeFee dustAssetRedemptionRelativeFee; do
  query "$sig" cast call "$FEE" "$sig()(int256)" --block "$BLOCK" --rpc-url "$RPC"
done
query historical_feesetup_tx cast tx "$FEESETUP_TX" --json --rpc-url "$RPC"
query historical_feesetup_receipt cast receipt "$FEESETUP_TX" --json --rpc-url "$RPC"
echo "Eligibility includes filter logic, allowlists, exemptions, paused/cap conditions; cannot infer ALL from these calls." >> "$OUT/STATUS.txt"
echo "Historical matching requires repeat at the exact historical block(s)." >> "$OUT/STATUS.txt"
