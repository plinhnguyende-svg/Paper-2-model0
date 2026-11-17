#!/usr/bin/env python3
"""Read-only configured RPC preflight. Never print the endpoint or remote errors."""
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request
import urllib.parse
import urllib.error

CALCULATOR='0x6a4549759c475d845d4ae074b3656dc257490da5'
POOL='0x20b048fa035d5763685d695e66adf62c5d9f5055'
TX='0x1e4187be16964075654028ea7c92c02fc798d4bb097cab53efb5847cd85c91c0'
BLOCK=13197311
SLOT='0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'


def validate(call,save):
    assert int(call('eth_chainId',[]),16)==8453, 'wrong_chain'
    tx=call('eth_getTransactionByHash',[TX]);save('known_tx.json',tx)
    receipt=call('eth_getTransactionReceipt',[TX]);save('known_receipt.json',receipt)
    assert tx and receipt and receipt['transactionHash'].lower()==TX
    assert tx['hash'].lower()==TX and tx['to'].lower()==CALCULATOR
    assert int(receipt['status'],16)==1 and int(receipt['blockNumber'],16)==BLOCK
    block=call('eth_getBlockByNumber',[hex(BLOCK),False]);save('known_block.json',block)
    assert int(block['number'],16)==BLOCK and block['hash']==receipt['blockHash']==tx['blockHash']
    assert tx['transactionIndex']==receipt['transactionIndex']
    assert block['transactions'][int(receipt['transactionIndex'],16)].lower()==TX
    logs=call('eth_getLogs',[dict(address=CALCULATOR,fromBlock=hex(BLOCK),toBlock=hex(BLOCK))])
    save('known_block_logs.json',logs)
    expected=[x for x in receipt['logs'] if x['address'].lower()==CALCULATOR]
    assert expected, 'missing_known_calculator_log'
    for event in expected:
        assert any(all(candidate.get(k)==event.get(k) for k in ['transactionHash','blockHash','logIndex','address','topics','data']) for candidate in logs), 'missing_or_changed_log'
    code=call('eth_getCode',[POOL,hex(58258072)]);save('historical_pool_code.json',code)
    assert isinstance(code,str) and code not in ('0x','0x0'), 'empty_historical_code'
    implementation=call('eth_getStorageAt',[POOL,SLOT,hex(58258072)])
    save('checkpoint_implementation_slot.json',implementation)
    assert isinstance(implementation,str) and len(implementation)==66 and int(implementation,16)>0
    return dict(chain_id=8453,known_block=BLOCK,logs_matched=len(expected),historical_code='AVAILABLE',checkpoint_storage='AVAILABLE')


def main():
    out=Path(sys.argv[1] if len(sys.argv)>1 else 'transaction_evidence/rpc_preflight');out.mkdir(parents=True,exist_ok=True)
    def save(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n')
    url=os.environ.get('BASE_RPC_URL','').strip()
    status=dict(status='BLOCKED_MISSING_BASE_RPC_URL',credential_present=bool(url),full_history='NOT_TESTED',producer_attribution='UNVERIFIED')
    try:
        if not url:return 2
        status['stage']='endpoint_format'
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!='https' or not parsed.hostname or any(c.isspace() for c in url):
            status['failure_code']='EXPECTED_COMPLETE_HTTPS_RPC_URL'
            status['status']='RPC_CAPABILITY_FAIL'
            return 1
        status['endpoint_format']='VALID_HTTPS'
        def call(method,params):
            status['stage']=method
            body=json.dumps(dict(jsonrpc='2.0',id=1,method=method,params=params)).encode()
            req=urllib.request.Request(url,data=body,headers={'Content-Type':'application/json'})
            try:
                with urllib.request.urlopen(req,timeout=25) as response:payload=json.load(response)
            except urllib.error.HTTPError as exc:
                status['http_status']=exc.code
                raise
            if payload.get('error') or 'result' not in payload:raise RuntimeError('RPC_RESPONSE_ERROR')
            if method=='eth_chainId':
                status['received_chain_id']=int(payload['result'],16)
                status['expected_chain_id']=8453
                if status['received_chain_id']!=8453:status['failure_code']='WRONG_NETWORK'
            return payload['result']
        status.update(validate(call,save));status['status']='RPC_CAPABILITY_PASS_SAMPLE_ONLY'
        return 0
    except Exception as exc:
        status['status']='RPC_CAPABILITY_FAIL';status['error_type']=type(exc).__name__
        return 1
    finally:
        save('STATUS.json',status)
        save('SHA256.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='SHA256.json'})
        print(json.dumps(status))

if __name__=='__main__':sys.exit(main())
