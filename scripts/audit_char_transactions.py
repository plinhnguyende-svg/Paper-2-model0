#!/usr/bin/env python3
"""Read-only discovery with provider failover and narrow receipt reconciliation."""
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.parse
import urllib.request
from char_receipt_accounting import POOL,TRANSFER,ZERO,reconcile

SIGNATURES={
 'DepositFeePaid':'DepositFeePaid(address,uint256)',
 'RedeemFeePaid':'RedeemFeePaid(address,uint256)',
 'RedeemFeeBurnt':'RedeemFeeBurnt(address,uint256)',
 'Deposited':'Deposited(address,uint256)',
 'Redeemed':'Redeemed(address,address,uint256)'}


class Rpc:
    def __init__(self,out):
        self.out=out;self.failures=[];self.providers=[];self.cursor=0
        configured=os.environ.get('BASE_RPC_URL')
        choices=([('configured',configured)] if configured else [])+[
            ('drpc','https://base.drpc.org'),('publicnode','https://base-rpc.publicnode.com'),('base_public','https://mainnet.base.org')]
        for name,url in choices:
            try:
                if int(self.direct(url,'eth_chainId',[]),16)!=8453:raise ValueError('wrong chain')
                self.providers.append((name,url))
            except Exception as exc:self.failures.append(dict(provider=name,method='eth_chainId',error=type(exc).__name__))
        if not self.providers:raise RuntimeError('no verified Base RPC')

    def direct(self,url,method,params):
        r=subprocess.run(['cast','rpc',method,*[json.dumps(v) for v in params],'--rpc-url',url],capture_output=True,text=True,timeout=18)
        if r.returncode:
            detail=r.stderr.split('HTTP diagnostics:')[0].replace(url,'[RPC_REDACTED]')
            detail=re.sub(r'https?://\S+','[URL_REDACTED]',detail)[:600]
            raise RuntimeError(detail)
        return json.loads(r.stdout)

    def call(self,method,params):
        for offset in range(len(self.providers)):
            i=(self.cursor+offset)%len(self.providers);name,url=self.providers[i]
            try:
                value=self.direct(url,method,params);self.cursor=i
                return value,name
            except Exception as exc:
                self.failures.append(dict(provider=name,method=method,error=type(exc).__name__,detail=str(exc)[:600]))
        raise RuntimeError('all verified providers failed method')


def explorer_candidates(out,pages=4):
    """Indexer nominates txs; RPC receipts remain the source for accounting."""
    base=f'https://base.blockscout.com/api/v2/tokens/{POOL}/transfers'
    candidates=[];params={};errors=[]
    for page in range(pages):
        url=base+('?' + urllib.parse.urlencode(params) if params else '')
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'CHAR-research-readonly/1.0','Accept':'application/json'})
            with urllib.request.urlopen(req,timeout=15) as response:data=json.load(response)
            (out/f'explorer_page_{page}.json').write_text(json.dumps(data,indent=2)+'\n')
            for item in data.get('items',[]):
                tx=item.get('transaction_hash')
                sender=(item.get('from') or {}).get('hash','').lower()
                recipient=(item.get('to') or {}).get('hash','').lower()
                if tx and re.fullmatch(r'0x[0-9a-fA-F]{64}',tx) and (sender==ZERO or recipient==ZERO) and tx not in candidates:candidates.append(tx)
            params=data.get('next_page_params')
            if not params or len(candidates)>=12:break
            time.sleep(.3)
        except Exception as exc:
            errors.append(dict(page=page,error=type(exc).__name__));break
    return candidates,errors


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--start',type=int,required=True);p.add_argument('--end',type=int,required=True)
    p.add_argument('--out',required=True);p.add_argument('--max-receipts',type=int,default=12)
    args=p.parse_args()
    if not 0<=args.start<=args.end:p.error('invalid block interval')
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    summary=dict(chain_id=8453,pool=POOL,collected_at_utc=datetime.now(timezone.utc).isoformat(),selection='bounded indexer mint/burn candidates, then declared-range log fallback; not representative',
                 status='NOT_VERIFIED',candidates=[],scan_status='NOT_SCANNED',
                 prestate_and_formula='OPEN',producer_attribution='UNVERIFIED',economic_calibration='NOT_ESTABLISHED')
    rpc=None
    def save(name,data):(out/name).write_text(json.dumps(data,indent=2)+'\n')
    try:
        topics={name:subprocess.check_output(['cast','keccak',signature],text=True).strip() for name,signature in SIGNATURES.items()}
        save('EVENT_SIGNATURES.json',dict(zip(SIGNATURES.values(),topics.values())))
        candidates,errors=explorer_candidates(out);summary['explorer_errors']=errors
        summary['indexer_candidates']=len(candidates)
        rpc=Rpc(out)
        if not candidates:
            summary['scan_status']='IN_PROGRESS';complete=True
            # Same declared historical window, with wider batches and method failover.
            windows=[(args.start,args.end,1000),(13190000,13210000,1000)]
            summary['discovery_windows']=[dict(start=a,end=b,chunk=c) for a,b,c in windows]
            chunks=[(a,min(a+c-1,b)) for lo,b,c in windows for a in range(lo,b+1,c)]
            for start,end in chunks:
                try:
                    logs,provider=rpc.call('eth_getLogs',[dict(address=POOL,fromBlock=hex(start),toBlock=hex(end),topics=[TRANSFER])])
                    save(f'logs_{start}_{end}.json',dict(provider=provider,logs=logs))
                    for log in logs:
                        if len(log.get('topics',[]))==3 and ('0x'+'0'*64) in log['topics'][1:]:
                            if log['transactionHash'] not in candidates:candidates.append(log['transactionHash'])
                    if len(candidates)>=12:
                        summary['scan_status']='BOUNDED_SAMPLE_EARLY_STOP';break
                except Exception:
                    complete=False;summary['scan_status']='INCOMPLETE_RPC_FAILURE';break
            else:summary['scan_status']='DECLARED_WINDOW_COMPLETE' if complete else 'INCOMPLETE_RPC_FAILURE'
        else:summary['scan_status']='INDEXER_SAMPLE_NOT_FULL_HISTORY'
        for txhash in candidates[:args.max_receipts]:
            row=dict(tx_hash=txhash,status='CANDIDATE_ONLY');summary['candidates'].append(row)
            try:
                tx,txprovider=rpc.call('eth_getTransactionByHash',[txhash])
                receipt,provider=rpc.call('eth_getTransactionReceipt',[txhash])
                block,_=rpc.call('eth_getBlockByNumber',[receipt['blockNumber'],False])
                assert receipt['transactionHash']==txhash and receipt['blockHash']==tx['blockHash']==block['hash']
                assert receipt['transactionIndex']==tx['transactionIndex']
                assert block['transactions'][int(receipt['transactionIndex'],16)]==txhash
                assert int(receipt['status'],16)==1
                save(txhash+'_tx.json',tx);save(txhash+'_receipt.json',receipt);save(txhash+'_block.json',block)
                accounting=reconcile(receipt,topics);save(txhash+'_accounting.json',accounting)
                row.update(block=int(receipt['blockNumber'],16),tx_index=int(receipt['transactionIndex'],16),
                           provider=provider,status=accounting['status'],kind=accounting.get('kind'),
                           amount_raw=accounting.get('amount_raw'),fee_raw=accounting.get('fee_raw'),
                           canonical_identity='MATCHED')
                print(json.dumps(row),flush=True)
                if accounting['status']=='RECEIPT_ACCOUNTING_MATCH' and 'trace_attempt' not in summary:
                    summary['trace_attempt']={}
                    for tracer in ['callTracer','prestateTracer']:
                        try:
                            trace,traceprovider=rpc.call('debug_traceTransaction',[txhash,dict(tracer=tracer,timeout='10s')])
                            save(txhash+'_'+tracer+'.json',dict(provider=traceprovider,result=trace))
                            summary['trace_attempt'][tracer]='CAPTURED_NOT_RECONCILED'
                        except Exception:summary['trace_attempt'][tracer]='UNAVAILABLE'
                if sum(r['status']=='RECEIPT_ACCOUNTING_MATCH' for r in summary['candidates'])>=3:break
            except Exception as exc:row['error']=type(exc).__name__
        matched=sum(r['status']=='RECEIPT_ACCOUNTING_MATCH' for r in summary['candidates'])
        summary['matched_receipts']=matched
        summary['status']='RECEIPT_SAMPLE_ACCOUNTING_PASS_FULL_RECONCILIATION_OPEN' if matched else 'NO_MATCHED_RECEIPT_SAMPLE'
    except Exception as exc:summary['error']=type(exc).__name__
    finally:
        if rpc:save('RPC_FAILURES.json',rpc.failures)
        fields=['tx_hash','block','tx_index','kind','amount_raw','fee_raw','provider','canonical_identity','status']
        with (out/'ACTUAL_RECEIPT_ACCOUNTING.csv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
            for row in summary['candidates']:
                if row['status']=='RECEIPT_ACCOUNTING_MATCH':writer.writerow({k:row.get(k) for k in fields})
        save('SUMMARY.json',summary)
        save('SHA256.json',{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file() and f.name!='SHA256.json'})
        print(json.dumps(summary,indent=2))
    return 0 if summary.get('matched_receipts',0)>0 else 1


if __name__=='__main__':raise SystemExit(main())
