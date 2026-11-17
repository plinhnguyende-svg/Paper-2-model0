#!/usr/bin/env python3
"""Gate29 transaction-panel enrichment: honest B-1/B snapshots and two separately
proven transaction-index-aware Gate25 references.

B-1 and B are NEVER mislabeled as exact transaction pre/post state.
A complete event-sourced replay or Foundry per-transaction fork is needed for
actual intra-block state. Project share is not full multi-project HHI.
"""
import argparse
import csv
from datetime import datetime,timezone
from decimal import Decimal,localcontext
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from gate29_event_census import Rpc, as_int, POOL, CALC, save_json

IMPLEMENTATION_SLOT="0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
VINTAGE_DATA_SELECTOR="0x3633f35f"
LEGACY_PROJECT_INVENTORY_SELECTOR="0x875bf3b5"
VERIFIED_GATE25={
    "0x0237beb377836c8ca1bec693cc5d37eff65d3a48b53b68d667fed67839b8193c":{
      "kind":"deposit",
      "amount_raw":18000000000000000000,
      "token":"0x99f5f445ff1f537686f2fbc32d43653c7c786645",
      "project_id":13,
      "pre_total_raw":81950000000000000000,
      "pre_project_raw":0,
      "actual_fee_raw":299055716169059513,
      "implementation":"0xb61763cf40e53df924856925461d5914c274ecd8"
    },
    "0xc676a373fc6cec24dd9f744f04a7dd7f975921370be6270185006b25fbd4f034":{
      "kind":"redemption",
      "amount_raw":5000000000000000,
      "token":"0xf20cb470acda661ab02de3b7be43894e2ade0b1c",
      "project_id":6,
      "pre_total_raw":594950000000000000000,
      "pre_project_raw":499000000000000000000,
      "actual_fee_raw":9412065557460,
      "implementation":"0xb61763cf40e53df924856925461d5914c274ecd8"
    }
}


def sig(signature):
    return subprocess.check_output(["cast","sig",signature],text=True).strip()


def eth_call_int(rpc,address,selector,block,data=""):
    value=rpc.call("eth_call",[{"to":address,"data":selector+data},hex(block)])
    if not isinstance(value,str) or len(value)<66:
        raise ValueError("EMPTY_HISTORICAL_CALL_"+selector[:10])
    return int(value[:66],16)


def eth_call_address(rpc,address,selector,block):
    value=rpc.call("eth_call",[{"to":address,"data":selector},hex(block)])
    if not isinstance(value,str) or len(value)!=66:
        raise ValueError("INVALID_ADDRESS_RETURN")
    return "0x"+value[-40:].lower()


def get_vintage_project_id(rpc,token,block):
    raw=rpc.call("eth_call",[{"to":token,"data":VINTAGE_DATA_SELECTOR},hex(block)])
    if not isinstance(raw,str) or not raw.startswith("0x"):
        raise ValueError("TCO2_VINTAGE_METADATA_UNAVAILABLE")
    words=[raw[2+i:2+i+64] for i in range(0,len(raw)-2,64)]
    # Gate25 verifies offset=32 and the fourth tuple static word,
    # which is ABI return word index 4 (after the initial dynamic offset).
    if len(words)<5 or int(words[0],16)!=32:
        raise ValueError("TCO2_VINTAGE_METADATA_LAYOUT_MISMATCH")
    pid=int(words[4],16)
    if pid<=0 or pid>10**18:
        raise ValueError("INVALID_TCO2_PROJECT_ID")
    return pid


def raw_state(rpc,token,block,selectors):
    pool_calc=eth_call_address(rpc,POOL,selectors["feeCalculator"],block)
    slot=rpc.call("eth_getStorageAt",[POOL,IMPLEMENTATION_SLOT,hex(block)])
    if not isinstance(slot,str) or len(slot)!=66:
        raise ValueError("POOL_IMPLEMENTATION_SLOT_INVALID")
    implementation="0x"+slot[-40:].lower()
    total=eth_call_int(rpc,POOL,selectors["totalTCO2Supply"],block)
    project_id=get_vintage_project_id(rpc,token,block)
    perproject=eth_call_int(rpc,POOL,LEGACY_PROJECT_INVENTORY_SELECTOR,
                            block,format(project_id,"064x"))
    if perproject>total:
        raise ValueError("PROJECT_INVENTORY_EXCEEDS_TOTAL")
    setup={}
    for key in ("depositFeeScale","depositFeeRatioScale","redemptionFeeScale","redemptionFeeShift"):
        try:
            fee=eth_call_int(rpc,pool_calc,selectors[key],block)
            if fee>=1<<255:
                fee-=1<<256
            setup[key]=fee
        except Exception as exc:
            setup[key]=None
    return {
        "block":block,"calculator":pool_calc,"implementation":implementation,
        "project_id":project_id,"total_raw":total,"project_raw":perproject,
        "project_share":str(Decimal(perproject)/Decimal(total)) if total else None,
        "fee_configuration_raw":setup,
        "status":"END_OF_BLOCK_CHAIN_STATE_NOT_EXACT_EVENT_STATE"
    }


def reference_enrichment(row):
    ref=VERIFIED_GATE25.get(row.get("tx_hash",""))
    if not ref:
        return False
    if (row.get("transaction_type")!=ref["kind"]
         or row.get("amount_raw")!=ref["amount_raw"]
         or row.get("token","").lower()!=ref["token"]
         or (row.get("actual_fee_raw") is not None and
             row["actual_fee_raw"]!=ref["actual_fee_raw"])):
        row["reference_error"]="GATE25_IDENTIFIERS_DO_NOT_MATCH"
        return False
    row["project_id"]=ref["project_id"]
    row["pre_total_raw"]=ref["pre_total_raw"]
    row["pre_project_raw"]=ref["pre_project_raw"]
    row["pre_project_share"]=str(Decimal(ref["pre_project_raw"])/Decimal(ref["pre_total_raw"]))
    row["transaction_index_aware_prestate"]="EXACT_PRE_TX_GATE25_VALIDATED"
    row["inventory_source"]="GATE25_FOUNDRY_FORK_BY_TRANSACTION_REFERENCE"
    row["project_metadata_source"]="GATE25_VERIFIED_TCO2_METADATA"
    row["pool_implementation"]=ref["implementation"]
    # Deliberately do not fabricate post-transaction state or entire HHI.
    return True


def enrich(out,args):
    panel_path=out/"EVENT_LEVEL_PANEL.csv"
    if not panel_path.exists():
        raise ValueError("GATE29_EVENT_LEVEL_PANEL_MISSING")
    with panel_path.open() as file:
        panel=list(csv.DictReader(file))
    if not panel:
        save_json(out/"PRESTATE_ENRICHMENT_SUMMARY.json",{
            "status":"NO_TRADE_EVENTS_IN_SCANNED_WINDOWS","rows":0})
        return
    for row in panel:
        for fld in ("amount_raw","actual_fee_raw","block","tx_index","log_index"):
            if row.get(fld) and row[fld] not in ("None",""):
                row[fld]=int(row[fld])
    by_block={}
    for row in panel:
        b=row["block"]
        by_block.setdefault(b,[]).append(row)
    # Reproducible, deterministic selection through earliest n distinct blocks.
    blocks=sorted(by_block)[:args.max_blocks]
    rpc=Rpc(os.environ.get("BASE_RPC_URL","").strip())
    if as_int(rpc.call("eth_chainId",[]))!=8453:
        raise ValueError("NOT_BASE_MAINNET")
    selectors={k:sig(k+"()") for k in
       ("feeCalculator","totalTCO2Supply","depositFeeScale",
        "depositFeeRatioScale","redemptionFeeScale","redemptionFeeShift")}
    success=0
    fail=0
    exact_refs=0
    snapshots=[]
    begin=time.monotonic()
    for row in panel:
        row["observed_full_pool_HHI"]="NOT_COMPUTED_PROJECT_VECTOR_UNAVAILABLE"
        row["pre_hhi"]=None
        row["post_hhi"]=None
        row["transaction_index_aware_prestate"]="NOT_YET_REPLAYED"
        row["inventory_source"]="NOT_VERIFIED"
        row["project_metadata_source"]="NOT_VERIFIED"
        row["block_boundary_source"]="NOT_QUERIED"
        if reference_enrichment(row):
            exact_refs+=1
    for b in blocks:
        if time.monotonic()-begin>args.max_seconds:
            break
        group=by_block[b]
        tokens=list(dict.fromkeys(x["token"] for x in group if x.get("token")))
        for token in tokens:
            if time.monotonic()-begin>args.max_seconds:
                break
            matching=[x for x in group if x.get("token")==token]
            try:
                before=raw_state(rpc,token,b-1,selectors)
                after=raw_state(rpc,token,b,selectors)
                success+=1
                snapshots.append(dict(block=b,token=token,
                                      B_minus_one=before,B_end=after,
                                      prestate_equals_B_minus_one=False,
                                      poststate_equals_B_end=False,
                                      exact_intrablock_state="UNPROVEN"))
                for row in matching:
                    row["block_boundary_source"]="HISTORICAL_RPC_B_MINUS_ONE_AND_B"
                    row["B_minus_1_total_raw"]=before["total_raw"]
                    row["B_minus_1_project_raw"]=before["project_raw"]
                    row["B_end_total_raw"]=after["total_raw"]
                    row["B_end_project_raw"]=after["project_raw"]
                    row["B_minus_1_project_share"]=before["project_share"]
                    row["B_end_project_share"]=after["project_share"]
                    row["B_minus_1_calculator"]=before["calculator"]
                    row["B_minus_1_implementation"]=before["implementation"]
                    row["B_minus_1_fee_scale_raw"]=before["fee_configuration_raw"]["depositFeeScale"]
                    row["B_minus_1_fee_ratio_raw"]=before["fee_configuration_raw"]["depositFeeRatioScale"]
                    row["B_minus_1_redemption_scale_raw"]=before["fee_configuration_raw"]["redemptionFeeScale"]
                    row["B_minus_1_redemption_shift_raw"]=before["fee_configuration_raw"]["redemptionFeeShift"]
                    row["B_minus_1_project_id"]=before["project_id"]
                    row["project_id"]=row["project_id"] or before["project_id"]
                    row["B_minus_1_project_id_source"]="TCO2_GETVINTAGEDATA_B_MINUS_ONE"
                    row["same_block_pool_actions_preceding"]=sum(
                        (other["tx_index"],other["log_index"])<
                        (row["tx_index"],row["log_index"]) for other in group)
            except Exception as exc:
                fail+=1
                snapshots.append(dict(block=b,token=token,status="B_BOUNDARY_FAILED",
                                      error_type=type(exc).__name__,
                                      explanation="No invented B-minus-one or event prestate"))
    output=out/"EVENT_LEVEL_PANEL_ENRICHED.csv"
    columns=list(dict.fromkeys(k for x in panel for k in x))
    with output.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore")
        w.writeheader()
        for x in panel:
            w.writerow({k:(json.dumps(v) if isinstance(v,(dict,list)) else v)
                        for k,v in x.items()})
    save_json(out/"HISTORICAL_BLOCK_BOUNDARIES.json",snapshots)
    summary={
        "status":"BLOCK_BOUNDARY_ENRICHMENT_PARTIAL_NOT_EXACT_PRE_TX_CENSUS",
        "trade_action_rows":len(panel),
        "distinct_blocks":len(by_block),
        "selected_blocks":len(blocks),
        "block_token_pairs_succeeded":success,
        "block_token_pairs_failed":fail,
        "exact_prestate_rows_from_independent_gate25_replay":exact_refs,
        "exact_state_coverage_not_claimed":True,
        "full_inventory_HHI_not_computed":True,
        "reason_HHI_not_computed":"actual pool may contain more than two projects; need complete per-project inventory vector",
        "reason_block_boundary_not_exact":"prior/later intra-block transactions can change state",
        "fee_config_block_minus_one_not_exact":"owner can modify configuration in same block",
        "max_seconds":args.max_seconds
    }
    save_json(out/"PRESTATE_ENRICHMENT_SUMMARY.json",summary)
    print(json.dumps(summary,indent=2),flush=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True)
    ap.add_argument("--max-blocks",type=int,default=25)
    ap.add_argument("--max-seconds",type=int,default=160)
    args=ap.parse_args()
    if args.max_blocks<0 or args.max_seconds<1:
        ap.error("invalid limits")
    enrich(Path(args.out),args)

if __name__=="__main__":
    main()
