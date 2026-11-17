#!/usr/bin/env python3
"""Gate 29 empirical-first, checkpointed on-chain event census.

Uses a single configured historical Base RPC secret read-only, never logs its URL.
An event window is counted as covered ONLY after successful eth_getLogs.
Coverage, canonical receipt reconciliation and exact pre-transaction state are
three SEPARATE properties. No missing events or unavailable calls are imputed.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from collections import Counter, defaultdict

from char_receipt_accounting import POOL, reconcile

CHAIN = 8453
CALC = "0x6a4549759c475d845d4ae074b3656dc257490da5"
POOL_EVENTS = {
    "Deposited": "Deposited(address,uint256)",
    "Redeemed": "Redeemed(address,address,uint256)",
    "DepositFeePaid": "DepositFeePaid(address,uint256)",
    "RedeemFeePaid": "RedeemFeePaid(address,uint256)",
    "RedeemFeeBurnt": "RedeemFeeBurnt(address,uint256)",
    "Upgraded": "Upgraded(address)",
    "FeeCalculatorUpdated": "FeeCalculatorUpdated(address)",
    "MinimumTCLSeedingThresholdUpdated": "MinimumTCLSeedingThresholdUpdated(uint256)",
    "SupplyCapUpdated": "SupplyCapUpdated(uint256)",
    "AddFeeExemptedTCO2": "AddFeeExemptedTCO2(address)",
    "RemoveFeeExemptedTCO2": "RemoveFeeExemptedTCO2(address)",
    "RedeemFeeExempted": "RedeemFeeExempted(address,bool)",
    "TCO2Bridged": "TCO2Bridged(uint32,address,uint256)",
    "TCO2RebalanceRequestCompleted": "TCO2RebalanceRequestCompleted(address[],uint256[])",
    "TCO2RebalanceRequestInitiated": "TCO2RebalanceRequestInitiated(uint32,address[],uint256[])",
    "Paused": "Paused(address)",
    "Unpaused": "Unpaused(address)"
}
CALC_EVENTS = {
    "DepositFeeScaleUpdated": "DepositFeeScaleUpdated(int256)",
    "DepositFeeRatioUpdated": "DepositFeeRatioUpdated(int256)",
    "RedemptionFeeScaleUpdated": "RedemptionFeeScaleUpdated(int256)",
    "RedemptionFeeShift": "RedemptionFeeShift(int256)",
    "SingleAssetDepositRelativeFeeUpdated": "SingleAssetDepositRelativeFeeUpdated(int256)",
    "SingleAssetRedemptionRelativeFeeUpdated": "SingleAssetRedemptionRelativeFeeUpdated(int256)",
    "DustAssetRedemptionRelativeFeeUpdated": "DustAssetRedemptionRelativeFeeUpdated(int256)",
    "FeeSetup": "FeeSetup(address[],uint256[])",
    "OwnershipTransferred": "OwnershipTransferred(address,address)"
}
TRADE_EVENTS = {"Deposited","Redeemed"}
FEE_EVENTS = {"DepositFeePaid","RedeemFeePaid","RedeemFeeBurnt"}
UTC = timezone.utc


def save_json(path, obj):
    path.write_text(json.dumps(obj,indent=2,sort_keys=True,default=str)+"\n")


def append_jsonl(path, rows):
    with path.open("a") as file:
        for row in rows:
            file.write(json.dumps(row,separators=(",",":"))+"\n")


def load_jsonl(path):
    if not path.exists():
        return []
    result=[]
    with path.open() as file:
        for line in file:
            if line.strip():
                result.append(json.loads(line))
    return result


def as_int(v):
    return int(v,16) if isinstance(v,str) and v.startswith("0x") else int(v)


def topic_map():
    full = {**POOL_EVENTS, **CALC_EVENTS}
    return {name:subprocess.check_output(["cast","keccak",sig],text=True).strip().lower()
            for name,sig in full.items()}


def valid_rpc_log(log, lower, upper, addresses, expected_topics):
    if not lower<=as_int(log["blockNumber"])<=upper:
        raise ValueError("LOG_OUT_OF_WINDOW")
    if log["address"].lower() not in addresses:
        raise ValueError("LOG_WRONG_ADDRESS")
    if not log.get("topics") or log["topics"][0].lower() not in expected_topics:
        raise ValueError("LOG_UNEXPECTED_SIGNATURE")
    if log.get("removed", False):
        raise ValueError("REMOVED_REORG_LOG")
    for field in ("transactionHash","blockHash","logIndex","transactionIndex"):
        if field not in log:
            raise ValueError("LOG_INCOMPLETE_"+field)
    return True


def covered_intervals(records):
    intervals=sorted((x["start"],x["end"]) for x in records
                     if x.get("status")=="SUCCESS")
    merged=[]
    for left,right in intervals:
        if merged and left<=merged[-1][1]+1:
            merged[-1]=(merged[-1][0],max(right,merged[-1][1]))
        else:
            merged.append((left,right))
    return merged


def missing_intervals(start,end,completed):
    """Exact complement of successful, inclusive block coverage."""
    out=[]
    cursor=start
    for a,b in completed:
        if b<cursor or a>end:
            continue
        if cursor<a:
            out.append((cursor,min(end,a-1)))
        cursor=max(cursor,b+1)
        if cursor>end:
            return out
    if cursor<=end:
        out.append((cursor,end))
    return out


def labels_for_log(log,topics):
    mapping={v:k for k,v in topics.items()}
    return mapping.get(log["topics"][0].lower(),"UNKNOWN")


class Rpc:
    def __init__(self, url):
        if not url.startswith("https://"):
            raise RuntimeError("BASE_RPC_URL_MUST_BE_HTTPS_SECRET")
        self.url=url
        self.calls=Counter()
        self.failures=Counter()
    def call(self,method,params):
        self.calls[method]+=1
        req=urllib.request.Request(self.url,
            data=json.dumps({"jsonrpc":"2.0","id":29,"method":method,
                             "params":params}).encode(),
            headers={"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=24) as response:
                obj=json.load(response)
        except Exception as exc:
            self.failures[method+"_"+type(exc).__name__]+=1
            raise RuntimeError("RPC_TRANSPORT_ERROR_"+method) from None
        if not isinstance(obj,dict) or "error" in obj or "result" not in obj:
            self.failures[method+"_JSONRPC_ERROR"]+=1
            raise RuntimeError("RPC_METHOD_UNAVAILABLE_OR_LIMITED_"+method)
        return obj["result"]


def ensure_consistency(logs):
    ordered=sorted(logs,key=lambda x:(as_int(x["blockNumber"]),
                 as_int(x["transactionIndex"]),as_int(x["logIndex"])))
    identities=set()
    for row in ordered:
        item=(row["transactionHash"].lower(),as_int(row["logIndex"]))
        if item in identities:
            raise ValueError("DUPLICATE_LOG_IDENTITY")
        identities.add(item)
    return ordered


def tx_candidates(logs,topics):
    return list(dict.fromkeys(x["transactionHash"].lower()
             for x in logs if labels_for_log(x,topics) in TRADE_EVENTS))


def extract_event_rows(logs,topics):
    rows=[]
    for x in ensure_consistency(logs):
        label=labels_for_log(x,topics)
        item={
            "block":as_int(x["blockNumber"]),
            "tx_index":as_int(x["transactionIndex"]),
            "log_index":as_int(x["logIndex"]),
            "tx_hash":x["transactionHash"].lower(),
            "contract":x["address"].lower(),
            "event":label,
            "raw_data":x["data"],
            "topic0":x["topics"][0].lower(),
            "topic1":x["topics"][1].lower() if len(x["topics"])>1 else ""
        }
        if label=="Deposited":
            words=[x["data"][k:k+64] for k in range(2,len(x["data"]),64)]
            if len(words)==2:
                item["token"]="0x"+words[0][-40:]
                item["amount_raw"]=int(words[1],16)
        elif label=="Redeemed":
            words=[x["data"][k:k+64] for k in range(2,len(x["data"]),64)]
            if len(words)==3:
                item["actor"]="0x"+words[0][-40:]
                item["token"]="0x"+words[1][-40:]
                item["amount_raw"]=int(words[2],16)
        elif label in FEE_EVENTS:
            words=[x["data"][k:k+64] for k in range(2,len(x["data"]),64)]
            if len(words)==2:
                item["actor"]="0x"+words[0][-40:]
                item["fee_raw"]=int(words[1],16)
        elif label in ("DepositFeeScaleUpdated","DepositFeeRatioUpdated",
                       "RedemptionFeeScaleUpdated","RedemptionFeeShift",
                       "SingleAssetDepositRelativeFeeUpdated",
                       "SingleAssetRedemptionRelativeFeeUpdated",
                       "DustAssetRedemptionRelativeFeeUpdated"):
            if len(x["data"])==66:
                v=int(x["data"],16)
                item["parameter_int256"]=v-(1<<256) if v>=1<<255 else v
        rows.append(item)
    return rows


def canonical_receipt(rpc,txhash,discovered):
    receipt=rpc.call("eth_getTransactionReceipt",[txhash])
    if not receipt or receipt.get("transactionHash","").lower()!=txhash:
        raise ValueError("CANONICAL_RECEIPT_MISSING")
    if as_int(receipt["status"])!=1:
        raise ValueError("REVERTED_RECEIPT_WITH_SUCCESS_EVENT")
    tx=rpc.call("eth_getTransactionByHash",[txhash])
    if not tx or tx.get("blockHash")!=receipt.get("blockHash"):
        raise ValueError("TX_RECEIPT_BLOCK_MISMATCH")
    block=rpc.call("eth_getBlockByNumber",[receipt["blockNumber"],False])
    idx=as_int(receipt["transactionIndex"])
    if not block or idx>=len(block["transactions"]) or block["transactions"][idx].lower()!=txhash:
        raise ValueError("TX_NOT_AT_CANONICAL_INDEX")
    if block["hash"]!=receipt["blockHash"] or tx["transactionIndex"]!=receipt["transactionIndex"]:
        raise ValueError("TX_BLOCK_IDENTITY_MISMATCH")
    known={(y["blockHash"],as_int(y["logIndex"]),y["address"].lower(),
            tuple(v.lower() for v in y["topics"]),y["data"].lower())
           for y in receipt.get("logs",[])}
    for x in discovered:
        identity=(x["blockHash"],as_int(x["logIndex"]),x["address"].lower(),
                  tuple(v.lower() for v in x["topics"]),x["data"].lower())
        if identity not in known:
            raise ValueError("DISCOVERED_LOG_NOT_IN_RECEIPT")
    return tx,receipt,block


def receipt_row(rpc, txhash, discovered, topics):
    tx,receipt,block=canonical_receipt(rpc,txhash,discovered)
    matched=reconcile(receipt,{name:topics[name] for name in
       ("DepositFeePaid","RedeemFeePaid","RedeemFeeBurnt","Deposited","Redeemed")})
    record={
        "tx_hash":txhash,"block":as_int(receipt["blockNumber"]),
        "tx_index":as_int(receipt["transactionIndex"]),
        "timestamp_utc":datetime.fromtimestamp(as_int(block["timestamp"]),UTC).isoformat(),
        "timestamp_unix":as_int(block["timestamp"]),
        "actor":matched.get("actor"),
        "token":matched.get("underlying"),
        "transaction_type":matched.get("kind") or "UNCLASSIFIED",
        "amount_raw":matched.get("amount_raw"),
        "actual_fee_raw":matched.get("fee_raw"),
        "effective_fee_rate":(
            str(matched["fee_raw"]/matched["amount_raw"])
            if matched.get("amount_raw") and matched.get("fee_raw") is not None else None),
        "receipt_accounting_status":matched["status"],
        "receipt_checks":matched.get("checks",{}),
        "canonical_identity":"VALIDATED",
        "block_start_is_exact_pre_transaction":False,
        "exact_transaction_prestate":"NOT_YET_REPLAYED"
    }
    # Preserve individual on-chain recipient amounts, but NOT label them producers.
    record["recipient_token_flows"]=[
         {"address":x["recipient"],"amount_raw":x["amount_raw"]}
         for x in matched.get("observed_fee_destinations",[])]
    return record,receipt


def census(rpc,out,args,topics):
    journal=out/"POOL_SCAN_JOURNAL.jsonl"
    rawlog=out/"POOL_LOGS.jsonl"
    existing=load_jsonl(journal)
    if rawlog.exists() and not journal.exists():
        raise ValueError("UNMATCHED_RAW_LOGS_WITHOUT_SCAN_LEDGER")
    old_logs=load_jsonl(rawlog)
    successes=covered_intervals(existing)
    head=as_int(rpc.call("eth_blockNumber",[]))
    end=head if args.end_block is None else min(head,args.end_block)
    if args.start_block>end:
        raise ValueError("START_BEYOND_HEAD")
    groups=missing_intervals(args.start_block,end,successes)
    work=[]
    for a,b in groups:
        for left in range(a,b+1,args.chunk):
            work.append((left,min(b,left+args.chunk-1)))
    calls=0
    failures=0
    started=time.monotonic()
    available=set(topics[name] for name in POOL_EVENTS)
    while work:
        if calls>=args.max_log_calls or time.monotonic()-started>=args.max_seconds:
            break
        left,right=work.pop(0)
        calls+=1
        try:
            logs=rpc.call("eth_getLogs",[{
                "address":POOL,"fromBlock":hex(left),"toBlock":hex(right),
                "topics":[sorted(available)]}])
            if not isinstance(logs,list):
                raise ValueError("INVALID_LOG_LIST")
            for x in logs:
                valid_rpc_log(x,left,right,{POOL},available)
            # Write discovered log items BEFORE marking interval scanned.
            # On interruption after raw log write but before journal write,
            # next run deduplicates by txHash/logIndex, and still rescans.
            append_jsonl(rawlog,logs)
            append_jsonl(journal,[{
                "start":left,"end":right,"status":"SUCCESS",
                "logs":len(logs),"at_utc":datetime.now(UTC).isoformat()}])
            old_logs.extend(logs)
        except Exception:
            failures+=1
            if left<right:
                mid=(left+right)//2
                work[0:0]=[(left,mid),(mid+1,right)]
            else:
                append_jsonl(journal,[{"start":left,"end":right,
                              "status":"FAILED_SINGLE_BLOCK"}])
        if calls%50==0:
            print(json.dumps({"phase":"pool_log_scan","calls":calls,
                      "events_raw":len(old_logs),"next_unscanned":work[0] if work else None}),
                  flush=True)
    unique={}
    for log in old_logs:
        key=(log["transactionHash"].lower(),as_int(log["logIndex"]))
        if key in unique:
            if unique[key]!=log:
                raise ValueError("REPLAYED_LOG_DIFFERS_FROM_EXISTING_LEDGER")
        unique[key]=log
    raw=ensure_consistency(list(unique.values()))
    complete=covered_intervals(load_jsonl(journal))
    gaps=missing_intervals(args.start_block,end,complete)
    return dict(logs=raw,head=head,end=end,log_calls=calls,
                log_failures=failures,completed=complete,gaps=gaps,
                complete=(len(gaps)==0),elapsed_sec=round(time.monotonic()-started,2),
                log_budget_exhausted=(len(work)>0))


def scan_calculator_events(rpc,out,args,topics, pool_logs):
    """Only known verified calculator address; all other calculator versions
    must be separately discovered and queried before claiming complete configs."""
    directory=out/"CALCULATOR";directory.mkdir(exist_ok=True)
    journal=directory/"SCAN_JOURNAL.jsonl"
    rawlog=directory/"LOGS.jsonl"
    earlier=load_jsonl(journal)
    logs=load_jsonl(rawlog)
    all_addresses={CALC}
    # FeeCalculatorUpdated emits a non-indexed address in one ABI word.
    for x in pool_logs:
        if x["topics"][0].lower()==topics["FeeCalculatorUpdated"] and len(x["data"])==66:
            new="0x"+x["data"][-40:].lower()
            if int(new,16)!=0:
                all_addresses.add(new)
    all_addresses=sorted(all_addresses)
    # Keep calculator scan budget separate; leave any gaps explicit.
    head=as_int(rpc.call("eth_blockNumber",[]))
    end=head if args.end_block is None else min(head,args.end_block)
    queries=0
    start_at=time.monotonic()
    allowed={topics[k] for k in CALC_EVENTS}
    for address in all_addresses:
        records=[x for x in earlier if x.get("address")==address]
        completed=covered_intervals(records)
        for start,endgap in missing_intervals(args.start_block,end,completed):
            for left in range(start,endgap+1,args.chunk):
                work=[(left,min(endgap,left+args.chunk-1))]
                while work and queries<args.max_calc_log_calls and \
                        time.monotonic()-start_at<args.max_calc_seconds:
                    a,b=work.pop(0)
                    queries+=1
                    try:
                        found=rpc.call("eth_getLogs",[{
                            "address":address,"fromBlock":hex(a),"toBlock":hex(b),
                            "topics":[sorted(allowed)]}])
                        for log in found:
                            valid_rpc_log(log,a,b,{address},allowed)
                        append_jsonl(rawlog,found)
                        append_jsonl(journal,[{"address":address,"start":a,"end":b,
                                   "status":"SUCCESS","logs":len(found)}])
                        logs.extend(found)
                    except Exception:
                        if a<b:
                            middle=(a+b)//2
                            work[0:0]=[(a,middle),(middle+1,b)]
                        else:
                            append_jsonl(journal,[{"address":address,"start":a,"end":b,
                                               "status":"FAILED_SINGLE_BLOCK"}])
                if queries>=args.max_calc_log_calls or \
                        time.monotonic()-start_at>=args.max_calc_seconds:
                    break
            if queries>=args.max_calc_log_calls or \
                    time.monotonic()-start_at>=args.max_calc_seconds:
                break
    found_unique={}
    for log in logs:
        key=(log["transactionHash"].lower(),as_int(log["logIndex"]))
        if key in found_unique and found_unique[key]!=log:
            raise ValueError("CALCULATOR_LOG_CONFLICT")
        found_unique[key]=log
    final=ensure_consistency(list(found_unique.values()))
    cover={}
    for address in all_addresses:
        records=[x for x in load_jsonl(journal) if x.get("address")==address]
        cover[address]=missing_intervals(args.start_block,end,covered_intervals(records))
    return dict(logs=final,addresses=all_addresses,gaps=cover,
                complete=all(not x for x in cover.values()),log_calls=queries)


def receipt_audit(rpc,out,args,pool_logs,topics):
    by_tx=defaultdict(list)
    for x in pool_logs:
        by_tx[x["transactionHash"].lower()].append(x)
    candidate=tx_candidates(pool_logs,topics)
    archive=out/"RECEIPTS";archive.mkdir(exist_ok=True)
    oldrows={x["tx_hash"]:x for x in load_jsonl(out/"RECEIPT_ROWS.jsonl")}
    added=[]
    count=0
    for txhash in candidate:
        if txhash in oldrows:
            continue
        if count>=args.max_receipts or count>=args.max_receipt_errors+args.max_receipts:
            break
        count+=1
        try:
            row,raw=receipt_row(rpc,txhash,by_tx[txhash],topics)
            save_json(archive/(txhash+".json"),raw)
        except Exception as exc:
            row=dict(tx_hash=txhash,receipt_accounting_status="UNVERIFIED",
                     error_type=type(exc).__name__,
                     error_code=str(exc)[:80] if isinstance(exc,ValueError) else "RPC_OR_PARSE_ERROR")
        append_jsonl(out/"RECEIPT_ROWS.jsonl",[row])
        added.append(row)
        if count%25==0:
            print(json.dumps({"phase":"receipt_audit","processed":count,
                             "total_candidates":len(candidate)}),flush=True)
    merged={**oldrows,**{x["tx_hash"]:x for x in added}}
    return dict(rows=sorted(merged.values(),key=lambda x:(x.get("block",10**18),
                    x.get("tx_index",10**6))),
                candidate_count=len(candidate),
                processed_count=len(merged),
                new_processed=len(added),
                unprocessed_candidates=len(set(candidate)-set(merged)))


def write_panel(out, rows, event_rows,topics):
    # A unique action is one deposit/redeem emitted event; multi-action receipts
    # are not assigned a fabricated unique receipt-level fee.
    by_tx=defaultdict(list)
    for x in event_rows:
        by_tx[x["tx_hash"]].append(x)
    by_receipt={x["tx_hash"]:x for x in rows}
    panel=[]
    for txhash,logs in by_tx.items():
        actions=[x for x in logs if x["event"] in TRADE_EVENTS]
        feeevents=[x for x in logs if x["event"] in FEE_EVENTS]
        record=by_receipt.get(txhash,{})
        for index,action in enumerate(actions):
            kind="deposit" if action["event"]=="Deposited" else "redemption"
            matched=(record.get("transaction_type")==kind and
                     record.get("receipt_accounting_status")=="RECEIPT_ACCOUNTING_MATCH"
                     and len(actions)==1)
            fee=(record.get("actual_fee_raw") if matched else None)
            amount=action.get("amount_raw")
            panel.append({
                "tx_hash":txhash,
                "block":action["block"],"tx_index":action["tx_index"],
                "log_index":action["log_index"],"action_index_in_tx":index,
                "timestamp_utc":record.get("timestamp_utc"),
                "transaction_type":kind,
                "token":action.get("token"),
                "actor":record.get("actor") if matched else action.get("actor"),
                "amount_raw":amount,
                "actual_fee_raw":fee,
                "effective_fee_rate":str(fee/amount) if fee is not None and amount else None,
                "fee_events_in_transaction":len(feeevents),
                "fee_attribution":("UNAMBIGUOUS_CANONICAL_RECEIPT"
                                   if matched else "NOT_RECONCILED_OR_MULTIACTION"),
                "receipt_status":record.get("receipt_accounting_status","NOT_FETCHED"),
                "project_id":None,"pre_total_raw":None,"pre_project_raw":None,
                "post_total_raw":None,"post_project_raw":None,
                "pre_hhi":None,"post_hhi":None,
                "fee_scale":None,"fee_ratio":None,"pool_implementation":None,
                "transaction_index_aware_prestate":"NOT_YET_REPLAYED",
                "inventory_source":"NOT_VERIFIED",
                "parameters_source":"NOT_VERIFIED",
                "project_metadata_source":"NOT_VERIFIED",
                "observability_note":"Receipt-level fees cannot be split among actions in a multicall without trace-specific allocation"
            })
    panel.sort(key=lambda x:(x["block"],x["tx_index"],x["log_index"]))
    keys=list(panel[0]) if panel else [
       "tx_hash","block","tx_index","transaction_type","timestamp_utc",
       "token","amount_raw","actual_fee_raw","fee_attribution",
       "pre_total_raw","pre_project_raw","post_total_raw","post_project_raw",
       "pre_hhi","post_hhi","project_id","fee_scale","pool_implementation",
       "transaction_index_aware_prestate"
    ]
    with (out/"EVENT_LEVEL_PANEL.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=keys)
        writer.writeheader()
        writer.writerows(panel)
    return panel


def identification_audit(panel,all_events,calc_events,pool_coverage,calc_coverage):
    trades=[x for x in panel if x["transaction_type"] in ("deposit","redemption")]
    receipts=[x for x in trades if x["receipt_status"]=="RECEIPT_ACCOUNTING_MATCH"]
    param=[x for x in calc_events if x["event"] in (
        "DepositFeeScaleUpdated","DepositFeeRatioUpdated",
        "RedemptionFeeScaleUpdated","RedemptionFeeShift")]
    unique_tx=len({x["tx_hash"] for x in trades})
    unique_token=len({x["token"] for x in trades if x["token"]})
    days=len({x["timestamp_utc"][:10] for x in receipts if x["timestamp_utc"]})
    actors=len({x["actor"] for x in receipts if x["actor"]})
    exact=sum(x["transaction_index_aware_prestate"]=="EXACT_PRE_TX" for x in trades)
    diagnoses={
        "pool_complete":pool_coverage["complete"],
        "calculator_complete":calc_coverage["complete"],
        "observed_trade_actions":len(trades),
        "observed_trade_transactions":unique_tx,
        "matched_receipt_actions":len(receipts),
        "observed_unique_tokens":unique_token,
        "receipt_observed_days":days,
        "receipt_observed_actors":actors,
        "verified_exact_pre_tx_rows":exact,
        "observed_fee_parameter_update_events":len(param),
        "known_calculator_addresses":calc_coverage["addresses"],
        "observability":{
          "fee_schedule_changes":"OBSERVED_EVENTS_ONLY_NOT_EXOGENOUS",
          "deposits_redemptions":"PROCESSED_EVENT_LOGS_ONLY",
          "nonparticipants":"UNOBSERVED",
          "valuation_and_outside_market":"UNOBSERVED",
          "actor_identity":"WALLET_NOT_PRODUCER",
          "credit_project_id":"NOT_YET_VERIFIED_IN_PANEL",
          "physical_removal_and_beta":"UNOBSERVED"
        }
    }
    if not pool_coverage["complete"] or not calc_coverage["complete"]:
        status="NOT_IDENTIFIED_INCOMPLETE_EVENT_CENSUS"
    elif not receipts or exact<len(trades):
        status="NOT_IDENTIFIED_INCOMPLETE_PRESTATE_OR_RECEIPTS"
    else:
        status="DESCRIPTIVE_POTENTIALLY_FEASIBLE_CAUSAL_UNIDENTIFIED"
    return dict(status=status,metrics=diagnoses,
                empirical_recommendation=(
                  "Do not estimate deposit/redemption price elasticity or causal fee effect "
                  "until pre-transaction state, policy change timing, actors and sufficient "
                  "as-if-exogenous variation are audited."),
                mechanical_simulation=(
                  "Permitted on fully reconciled fixed historical arrivals as accounting "
                  "counterfactuals only; no behavioral or welfare causal interpretation."),
                next_requirements=[
                  "Finish event-log and calculator-history coverage with zero gaps",
                  "Canonical receipt accounting for all distinct trade transactions",
                  "Read exact pre-transaction inventory and active fee setup for representative and then wider trades",
                  "Map TCO2 contract vintage project IDs and check rebalance/bridge state events",
                  "Separate observed config changes from inventory-generated endogenous quote changes",
                  "Report zero-trade opportunity sets and observed wallet inventory to evaluate choice-set identification"
                ])


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True)
    ap.add_argument("--start-block",type=int,default=0)
    ap.add_argument("--end-block",type=int)
    ap.add_argument("--chunk",type=int,default=100000)
    ap.add_argument("--max-seconds",type=int,default=270)
    ap.add_argument("--max-log-calls",type=int,default=900)
    ap.add_argument("--max-calc-seconds",type=int,default=90)
    ap.add_argument("--max-calc-log-calls",type=int,default=200)
    ap.add_argument("--max-receipts",type=int,default=140)
    ap.add_argument("--max-receipt-errors",type=int,default=40)
    args=ap.parse_args()
    if args.chunk<1 or args.start_block<0 or min(args.max_seconds,args.max_log_calls,
           args.max_receipts,args.max_calc_log_calls,args.max_calc_seconds)<=0:
        ap.error("invalid scan limits")
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    status={"status":"NOT_STARTED","chain_id":CHAIN,
        "collected_at_utc":datetime.now(UTC).isoformat(),
        "declared_start_block":args.start_block,
        "objective":"EMPIRICAL_FIRST_FULL_EVENT_HISTORY_WITH_EXPLICIT_COVERAGE",
        "not_established":["event-census completeness","exact transaction-index prestate",
                           "causal behavioral elasticity","producer identity","financial additionality"]}
    rpc=None
    try:
        url=os.environ.get("BASE_RPC_URL","").strip()
        rpc=Rpc(url)
        chain=as_int(rpc.call("eth_chainId",[]))
        if chain!=CHAIN:
            raise RuntimeError("WRONG_CHAIN_NOT_BASE")
        topics=topic_map()
        save_json(out/"EVENT_TOPICS.json",topics)
        pool=census(rpc,out,args,topics)
        calc=scan_calculator_events(rpc,out,args,topics,pool["logs"])
        events=extract_event_rows(pool["logs"]+calc["logs"],topics)
        append_file=out/"ALL_DECODED_EVENTS.json"
        save_json(append_file,events)
        receipts=receipt_audit(rpc,out,args,pool["logs"],topics)
        panel=write_panel(out,receipts["rows"],events,topics)
        audit=identification_audit(panel,events,
                                  [x for x in events if x["contract"]!=POOL],
                                  pool,calc)
        save_json(out/"IDENTIFICATION_AUDIT.json",audit)
        gap_report=dict(
           start=args.start_block,end=pool["end"],head=pool["head"],
           pool_complete=pool["complete"],pool_missing_count=len(pool["gaps"]),
           pool_first_missing_ranges=pool["gaps"][:60],
           pool_successful_scanned_segments=len(pool["completed"]),
           pool_successful_covered_blocks=sum(b-a+1 for a,b in pool["completed"]),
           calculator_addresses=calc["addresses"],calculator_complete=calc["complete"],
           calculator_first_gaps={k:v[:20] for k,v in calc["gaps"].items()},
           cap_warning="Calculator address roster comes from pool updates only if those updates were scanned")
        save_json(out/"COVERAGE_MANIFEST.json",gap_report)
        status.update(
           status=("COMPLETE_CENSUS_PENDING_PRESTATE" if pool["complete"] and
                calc["complete"] and receipts["unprocessed_candidates"]==0 else
                "PARTIAL_CENSUS_NOT_FULL_HISTORY"),
           declared_end_block=pool["end"],rpc_head_at_run=pool["head"],
           pool_log_calls=pool["log_calls"],pool_event_logs=len(pool["logs"]),
           calculator_log_calls=calc["log_calls"],
           calculator_event_logs=len(calc["logs"]),
           pool_scan_complete=pool["complete"],
           calculator_scan_complete=calc["complete"],
           receipt_candidates=receipts["candidate_count"],
           receipts_checked=receipts["processed_count"],
           receipts_remaining=receipts["unprocessed_candidates"],
           receipt_accounting_matches=sum(x.get("receipt_accounting_status")==
                    "RECEIPT_ACCOUNTING_MATCH" for x in receipts["rows"]),
           trade_action_rows=len(panel),
           exact_prestate_rows=0,
           identification_status=audit["status"],
           provider_failures=dict(rpc.failures),
           provider_calls=dict(rpc.calls),
           proxy_code_provenance="Gate27 separately verified for two versions; not all tx",
           fee_formula_replay="Gate25 two exemplars, not automatically every panel row",
           project_id_and_exact_prestate="NOT_INFERRED_FROM_BLOCK_END",
           producer_attribution="NOT_ESTABLISHED")
        print(json.dumps({k:v for k,v in status.items()
             if k not in ("provider_calls","provider_failures")},indent=2),flush=True)
    except Exception as exc:
        status.update(status="FAILED_OR_PARTIAL",failure=type(exc).__name__,
                      error_code=str(exc)[:100] if isinstance(exc,ValueError) else "REDACTED")
        print(json.dumps({"status":status["status"],"failure":status["failure"]}),flush=True)
    finally:
        save_json(out/"SUMMARY.json",status)
        digests={}
        for path in out.rglob("*"):
            if path.is_file() and path.name!="SHA256_MANIFEST.json":
                digests[str(path.relative_to(out))]=hashlib.sha256(path.read_bytes()).hexdigest()
        save_json(out/"SHA256_MANIFEST.json",digests)
    # Partial coverage is an expected empirical result, not a fake CI PASS for full history.
    return 0 if status["status"] in ("PARTIAL_CENSUS_NOT_FULL_HISTORY",
                 "COMPLETE_CENSUS_PENDING_PRESTATE") else 1

if __name__=="__main__":
    raise SystemExit(main())
