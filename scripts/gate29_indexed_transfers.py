#!/usr/bin/env python3
"""Gate29 indexed transfer discovery (OPTIONAL Alchemy read-only RPC capability).

Discover *candidate* historical CHAR mint and burn transactions via paginated
alchemy_getAssetTransfers; independently verify raw receipts and pool-emitted
Deposited/Redeemed events. This is never called a complete event log census:
transfers can miss nonmint/burn actions and service pagination may be incomplete.
No wallet-to-producer or benefit attribution is inferred.
"""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import time

from gate29_event_census import (
    Rpc,POOL,TRADE_EVENTS,POOL_EVENTS,topic_map,as_int,
    receipt_row,load_jsonl,append_jsonl,save_json
)
from char_receipt_accounting import ZERO


def find_transfer_candidates(rpc,out,topics,block_to,max_pages,stop_at):
    all_candidates=[]
    results={}
    all_complete=True
    for direction in ("mints_from_zero","burns_to_zero"):
        sub=out/direction
        sub.mkdir(parents=True,exist_ok=True)
        cursor_path=sub/"CURSOR.json"
        cursor=json.loads(cursor_path.read_text()) if cursor_path.exists() else {}
        # Existing successful pages are used before any new query.
        page_log=sub/"PAGES.jsonl"
        prior=load_jsonl(page_log)
        for r in prior:
            all_candidates.extend(r["candidate_hashes"])
        if cursor.get("done",False):
            results[direction]=dict(status="ALL_INDEXER_PAGES_READ",
                                    pages=len(prior),has_more=False)
            continue
        page_key=cursor.get("page_key")
        current=len(prior)
        while current<max_pages and time.monotonic()<stop_at:
            parameters={
               "fromBlock":"0x0","toBlock":hex(block_to),
               "contractAddresses":[POOL],"category":["erc20"],
               "maxCount":"0x3e8","withMetadata":False,
               "order":"asc","excludeZeroValue":False
            }
            if direction=="mints_from_zero":
                parameters["fromAddress"]=ZERO
            else:
                parameters["toAddress"]=ZERO
            if page_key:
                parameters["pageKey"]=page_key
            try:
                obj=rpc.call("alchemy_getAssetTransfers",[parameters])
                if not isinstance(obj,dict) or not isinstance(obj.get("transfers"),list):
                    raise ValueError("ALCHEMY_INDEXER_RESPONSE_SCHEMA_INVALID")
                transfers=obj["transfers"]
                records=[]
                for t in transfers:
                    h=t.get("hash","")
                    contract=(t.get("rawContract") or {}).get("address","")
                    if isinstance(h,str) and h.startswith("0x") and len(h)==66 and (
                      not contract or contract.lower()==POOL):
                        records.append(h.lower())
                records=list(dict.fromkeys(records))
                checksum=hashlib.sha256(json.dumps(
                    transfers,sort_keys=True,default=str).encode()).hexdigest()
                append_jsonl(page_log,[{
                    "page_index":current,"provider_transfer_count":len(transfers),
                    "candidate_hashes":records,"transfer_record_sha256":checksum,
                    "query_direction":direction,
                    "block_upper":block_to,
                    "service_page_key_was_present":bool(page_key)
                }])
                all_candidates.extend(records)
                page_key=obj.get("pageKey")
                current+=1
                save_json(cursor_path,{
                    "page_key":page_key,"done":not bool(page_key),
                    "last_page_index":current-1,"block_upper":block_to,
                    "source":"alchemy_getAssetTransfers_index_not_contract_logs"
                })
                if not page_key:
                    break
            except Exception as exc:
                results[direction]=dict(
                    status="INDEXER_METHOD_OR_PAGE_UNAVAILABLE",
                    failure_type=type(exc).__name__,
                    failure_code=str(exc) if str(exc).startswith(("RPC_","ALCHEMY_"))
                                       else "REDACTED",
                    pages=current,
                    pagination_complete=False)
                all_complete=False
                break
        if direction not in results:
            done=not bool(page_key)
            results[direction]=dict(
                status="ALL_INDEXER_PAGES_READ" if done else "INDEXER_PAGINATION_PARTIAL",
                pages=current,pagination_complete=done,has_more=bool(page_key))
            if not done:
                all_complete=False
        if direction=="mints_from_zero" and results[direction]["status"]=="INDEXER_METHOD_OR_PAGE_UNAVAILABLE":
            # Provider probably does not implement this Alchemy method.
            break
    return list(dict.fromkeys(all_candidates)),results,all_complete


def sample_receipts(rpc,out, candidates,topics,max_receipts,stop_at):
    checked={r["tx_hash"]:r for r in load_jsonl(out/"INDEXER_RECEIPT_ROWS.jsonl")}
    raw_events=load_jsonl(out/"INDEXER_VERIFIED_POOL_EVENTS.jsonl")
    key_event={ (x["transactionHash"].lower(),as_int(x["logIndex"])):x for x in raw_events}
    consumed=0
    pool_topics={topics[name] for name in POOL_EVENTS}
    for h in candidates:
        if h in checked:
            continue
        if consumed>=max_receipts or time.monotonic()>=stop_at:
            break
        consumed+=1
        try:
            r,receipt=receipt_row(rpc,h,[],topics)
            r["discovery_source"]="ALCHEMY_MINT_BURN_CANDIDATE_VERIFIED_BY_CANONICAL_RECEIPT"
            found=[x for x in receipt.get("logs",[]) if
                    x["address"].lower()==POOL and x.get("topics") and
                    x["topics"][0].lower() in pool_topics]
            if found:
                for x in found:
                    key=(x["transactionHash"].lower(),as_int(x["logIndex"]))
                    if key not in key_event:
                        key_event[key]=x
                        append_jsonl(out/"INDEXER_VERIFIED_POOL_EVENTS.jsonl",[x])
            r["pool_emitted_relevant_logs_in_receipt"]=len(found)
            r["trade_event_detected"]=any(x.get("topics",[""])[0].lower() in
                   (topics["Deposited"],topics["Redeemed"]) for x in found)
            if r["trade_event_detected"]:
                file=out/"INDEXER_RAW_RECEIPTS"/(h+".json")
                file.parent.mkdir(parents=True,exist_ok=True)
                save_json(file,receipt)
        except Exception as exc:
            r=dict(tx_hash=h,discovery_source="ALCHEMY_CANDIDATE",
                   trade_event_detected=False,
                   receipt_accounting_status="UNVERIFIED",
                   error_type=type(exc).__name__)
        checked[h]=r
        append_jsonl(out/"INDEXER_RECEIPT_ROWS.jsonl",[r])
        if consumed%30==0:
            print(json.dumps(dict(phase="indexer_receipts",checked_new=consumed,
                           total_candidates=len(candidates))),flush=True)
    verified=sum(bool(x.get("trade_event_detected")) for x in checked.values())
    return dict(candidate_transactions=len(candidates),receipts_checked=len(checked),
                receipts_new=consumed,verified_trade_receipts=verified,
                unresolved_candidate_receipts=len(candidates)-len(checked))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True)
    ap.add_argument("--max-pages",type=int,default=40)
    ap.add_argument("--max-receipts",type=int,default=100)
    ap.add_argument("--max-seconds",type=int,default=100)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    status=dict(status="NOT_TESTED",source="ALCHEMY_GETASSETTRANSFERS",
                full_event_census_claim=False,
                selection="ERC20 CHAR token mints from zero and burns to zero ONLY",
                causal_claim=False)
    try:
        rpc=Rpc(os.environ.get("BASE_RPC_URL","").strip())
        if as_int(rpc.call("eth_chainId",[]))!=8453:
            raise ValueError("WRONG_CHAIN")
        head=as_int(rpc.call("eth_blockNumber",[]))
        topics=topic_map()
        candidates,groups,pages_done=find_transfer_candidates(
           rpc,out,topics,head,args.max_pages,start+args.max_seconds/2)
        status.update(query_head=head,directions=groups,
                      candidates=len(candidates),
                      indexer_pages_complete=pages_done)
        status["receipt_audit"]=sample_receipts(
            rpc,out,candidates,topics,args.max_receipts,start+args.max_seconds)
        known_hashes=set(candidates)
        status["known_canary_deposit_candidate"]=(
           "0x0237beb377836c8ca1bec693cc5d37eff65d3a48b53b68d667fed67839b8193c"
           in known_hashes)
        status["known_canary_redemption_candidate"]=(
           "0xc676a373fc6cec24dd9f744f04a7dd7f975921370be6270185006b25fbd4f034"
           in known_hashes)
        status["status"]=(
          "INDEXED_CANDIDATES_PAGINATION_COMPLETE_NOT_LOG_CENSUS"
          if pages_done and all([status["known_canary_deposit_candidate"],
                                 status["known_canary_redemption_candidate"]])
          else "INDEXED_CANDIDATES_PARTIAL_OR_UNAVAILABLE")
    except Exception as exc:
        status["status"]="INDEXER_UNAVAILABLE"
        status["failure_type"]=type(exc).__name__
        status["safe_error"]=(str(exc) if str(exc).startswith(("RPC_","WRONG_CHAIN"))
                              else "REDACTED")
    finally:
        save_json(out/"INDEXER_SUMMARY.json",status)
        print(json.dumps(status,indent=2),flush=True)
    # Absence of provider-specific indexer is a feasibility result, not test failure.
    return 0


if __name__=="__main__":
    raise SystemExit(main())
