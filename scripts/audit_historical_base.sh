#!/usr/bin/env bash
# Historical same-block boundary snapshot; source EVM test != deployed EVM proof.
set -euo pipefail
RPC="${BASE_RPC_URL:-https://mainnet.base.org}"
TX="${1:-0x1e4187be16964075654028ea7c92c02fc798d4bb097cab53efb5847cd85c91c0}"
OUT="${2:-historical_base_evidence}"
POOL=0x20b048fA035D5763685D695e66aDF62c5D9F5055
ARTIFACT_CALC=0x6A4549759C475d845d4AE074B3656dC257490DA5
IMPL=0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc
BEACON=0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50
mkdir -p "$OUT"
if ! command -v cast >/dev/null; then echo NOT_EXECUTED_NO_CAST > "$OUT/STATUS.txt"; exit 0; fi
if ! cast receipt "$TX" --json --rpc-url "$RPC" > "$OUT/receipt.json" 2> "$OUT/receipt.error"; then
  echo UNVERIFIED_RECEIPT_UNAVAILABLE > "$OUT/STATUS.txt"; exit 0
fi
cast tx "$TX" --json --rpc-url "$RPC" > "$OUT/tx.json" 2> "$OUT/tx.error" || true
python3 - "$OUT/receipt.json" "$OUT/target_block.txt" <<'PY'
import json,sys
v=json.load(open(sys.argv[1]))["blockNumber"]
with open(sys.argv[2],"w") as f:f.write(str(int(v,16) if isinstance(v,str) and v.startswith("0x") else int(v)))
PY
BLOCK="$(cat "$OUT/target_block.txt")"
printf 'TX=%s\nBLOCK=%s\n' "$TX" "$BLOCK" > "$OUT/STATUS.txt"
capture() {
  local name="$1";shift
  if "$@" > "$OUT/$name.txt" 2> "$OUT/$name.err"; then
    echo "$name=OK" >> "$OUT/STATUS.txt"
  else
    echo "$name=FAILED" >> "$OUT/STATUS.txt"
  fi
}
for side in before after; do
  if [[ "$side" == before ]]; then B=$((BLOCK-1)); else B="$BLOCK"; fi
  capture "${side}_pool_bytecode" cast code "$POOL" --block "$B" --rpc-url "$RPC"
  capture "${side}_implementation_slot" cast storage "$POOL" "$IMPL" --block "$B" --rpc-url "$RPC"
  capture "${side}_beacon_slot" cast storage "$POOL" "$BEACON" --block "$B" --rpc-url "$RPC"
  capture "${side}_pool_version" cast call "$POOL" 'VERSION()(string)' --block "$B" --rpc-url "$RPC"
  capture "${side}_active_calculator" cast call "$POOL" 'feeCalculator()(address)' --block "$B" --rpc-url "$RPC"
  capture "${side}_pool_inventory" cast call "$POOL" 'totalUnderlyingSupply()(uint256)' --block "$B" --rpc-url "$RPC"
  capture "${side}_filter" cast call "$POOL" 'filter()(address)' --block "$B" --rpc-url "$RPC"
  capture "${side}_seeding_threshold" cast call "$POOL" 'minimumTCLSeedingThreshold()(uint256)' --block "$B" --rpc-url "$RPC"
  CALC="$ARTIFACT_CALC"
  if [[ -s "$OUT/${side}_active_calculator.txt" ]]; then
    found="$(sed -n 's/^\(0x[0-9a-fA-F]\{40\}\).*$/\1/p' "$OUT/${side}_active_calculator.txt" | head -1)"
    if [[ -n "$found" && "$found" != 0x0000000000000000000000000000000000000000 ]]; then CALC="$found";fi
  fi
  echo "$CALC" > "$OUT/${side}_calculator_address.txt"
  capture "${side}_calculator_bytecode" cast code "$CALC" --block "$B" --rpc-url "$RPC"
  capture "${side}_fee_recipients" cast call "$CALC" 'getFeeSetup()(address[],uint256[])' --block "$B" --rpc-url "$RPC"
  capture "${side}_fee_owner" cast call "$CALC" 'owner()(address)' --block "$B" --rpc-url "$RPC"
  for f in depositFeeScale depositFeeRatioScale redemptionFeeScale redemptionFeeShift singleAssetDepositRelativeFee singleAssetRedemptionRelativeFee dustAssetRedemptionRelativeFee; do
    capture "${side}_$f" cast call "$CALC" "$f()(int256)" --block "$B" --rpc-url "$RPC"
  done
done
cat >> "$OUT/STATUS.txt" <<'TXT'
Block B-1 and block B are boundary states, not exact intra-block pre-tx state.
FeeSetup tx is NOT proof CHAR pool was active at that block.
This does not verify token recipient identity or producer financing.
TXT
