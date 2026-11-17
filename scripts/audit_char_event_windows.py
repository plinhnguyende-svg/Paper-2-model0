#!/usr/bin/env python3
"""Gate 24: bounded pool-emitted event discovery, with auditable coverage.

Read-only. Events nominate transactions; receipts determine accounting.
This is NOT a historical census, fee-formula proof, or producer identification.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess

from audit_char_transactions import Rpc, SIGNATURES
from char_receipt_accounting import POOL, reconcile

EVENT_NAMES = ('DepositFeePaid', 'RedeemFeePaid', 'RedeemFeeBurnt',
               'Deposited', 'Redeemed')


def parse_windows(raw):
    windows = []
    for entry in raw.split(','):
        parts = entry.strip().split(':')
        if len(parts) != 2 or not all(x.isdigit() for x in parts):
            raise ValueError('expected start:end comma-separated decimal block windows')
        lo, hi = map(int, parts)
        if lo > hi or hi > 1000000000:
            raise ValueError('invalid block window')
        windows.append((lo, hi))
    if not windows:
        raise ValueError('at least one window is required')
    ordered = sorted(windows)
    if any(right[0] <= left[1] for left, right in zip(ordered, ordered[1:])):
        raise ValueError('overlapping windows are not permitted')
    return ordered


def validate_log(log, lo, hi, topics):
    height = int(log['blockNumber'], 16)
    if not lo <= height <= hi:
        raise ValueError('RPC log block outside requested interval')
    if log['address'].lower() != POOL:
        raise ValueError('RPC log from incorrect pool')
    if not log.get('topics') or log['topics'][0].lower() not in topics:
        raise ValueError('RPC log from unrequested event')
    if log.get('removed', False):
        raise ValueError('removed or reorganized log')
    if not log.get('transactionHash') or not log.get('blockHash'):
        raise ValueError('incomplete log identity')


def scan_window(rpc, lo, hi, topics, budget, ledger, found):
    """Adaptive split; only successful leaf intervals establish coverage."""
    if budget['used'] >= budget['limit']:
        ledger.append(dict(start=lo, end=hi, status='UNSCANNED_RPC_BUDGET'))
        return
    budget['used'] += 1
    try:
        logs, provider = rpc.call('eth_getLogs', [{
            'address': POOL,
            'fromBlock': hex(lo),
            'toBlock': hex(hi),
            'topics': [sorted(topics)]
        }])
        if not isinstance(logs, list):
            raise ValueError('invalid RPC log response')
        for item in logs:
            validate_log(item, lo, hi, topics)
        ledger.append(dict(start=lo, end=hi, status='SCANNED', provider=provider,
                           count=len(logs)))
        found.extend(logs)
    except Exception as exc:
        if lo == hi:
            ledger.append(dict(start=lo, end=hi, status='FAILED_SINGLE_BLOCK',
                               error_type=type(exc).__name__))
            return
        mid = (lo + hi) // 2
        scan_window(rpc, lo, mid, topics, budget, ledger, found)
        scan_window(rpc, mid + 1, hi, topics, budget, ledger, found)


def ordered_candidates(logs):
    ordered = sorted(logs, key=lambda l: (int(l['blockNumber'], 16),
                       int(l['transactionIndex'], 16), int(l['logIndex'], 16)))
    return list(dict.fromkeys(log['transactionHash'] for log in ordered))


def canonical_receipt(rpc, txhash, selected_logs):
    tx, _ = rpc.call('eth_getTransactionByHash', [txhash])
    receipt, provider = rpc.call('eth_getTransactionReceipt', [txhash])
    if not tx or not receipt or int(receipt['status'], 16) != 1:
        raise ValueError('missing or reverted canonical receipt')
    block, _ = rpc.call('eth_getBlockByNumber', [receipt['blockNumber'], False])
    i = int(receipt['transactionIndex'], 16)
    if not block or block['transactions'][i].lower() != txhash.lower():
        raise ValueError('transaction absent from canonical block')
    if not (receipt['transactionHash'].lower() == txhash.lower()
            and tx['hash'].lower() == txhash.lower()
            and tx['blockHash'] == receipt['blockHash'] == block['hash']
            and tx['transactionIndex'] == receipt['transactionIndex']):
        raise ValueError('canonical transaction/receipt identity mismatch')
    receipt_events = {(l['blockHash'], l['transactionHash'],
                       l['logIndex'], l['address'].lower(), tuple(l['topics']), l['data'])
                      for l in receipt['logs']}
    for log in selected_logs:
        identifier = (log['blockHash'], log['transactionHash'], log['logIndex'],
                      log['address'].lower(), tuple(log['topics']), log['data'])
        if identifier not in receipt_events:
            raise ValueError('discovered event missing from raw receipt')
    return tx, receipt, block, provider


def run(args, rpc_factory=Rpc):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    def save(name, obj):
        (out / name).write_text(json.dumps(obj, indent=2) + '\n')
    windows = parse_windows(args.windows)
    topics = {name: subprocess.check_output(
        ['cast', 'keccak', SIGNATURES[name]], text=True).strip().lower()
        for name in EVENT_NAMES}
    save('EVENT_TOPICS.json', topics)
    summary = dict(chain_id=8453, pool=POOL, windows=[dict(start=a, end=b) for a, b in windows],
                   collected_at_utc=datetime.now(timezone.utc).isoformat(),
                   methodology='direct eth_getLogs OR-filter for 5 pool event signatures; '
                   'adaptive split, canonical receipt verification; bounded scope only',
                   scope='selected block windows, not complete CHAR history',
                   status='NOT_VERIFIED', exact_fee_reproduction='OPEN',
                   producer_attribution='UNVERIFIED', beta='UNIDENTIFIED')
    ledger, found = [], []
    budget = dict(limit=args.max_rpc_calls, used=0)
    rpc = None
    try:
        rpc = rpc_factory(out)
        topics_set = set(topics.values())
        for a, b in windows:
            for start in range(a, b + 1, args.chunk):
                scan_window(rpc, start, min(b, start + args.chunk - 1),
                            topics_set, budget, ledger, found)
        save('EVENT_LOGS.json', found)
        save('SCAN_LEDGER.json', ledger)
        candidates = ordered_candidates(found)
        summary.update(rpc_log_calls=budget['used'], events=len(found),
                       candidate_transactions=len(candidates),
                       scan_complete=bool(ledger) and all(x['status']=='SCANNED' for x in ledger),
                       matched_receipts=0, receipt_errors=0, examined_receipts=0,
                       transaction_limit=args.max_receipts)
        result_rows = []
        by_tx = {key: [x for x in found if x['transactionHash'] == key]
                 for key in candidates}
        for txhash in candidates[:args.max_receipts]:
            row = dict(tx_hash=txhash, status='UNVERIFIED')
            try:
                tx, receipt, block, provider = canonical_receipt(rpc, txhash, by_tx[txhash])
                account = reconcile(receipt, topics)
                save(txhash + '_tx.json', tx)
                save(txhash + '_receipt.json', receipt)
                save(txhash + '_block.json', block)
                save(txhash + '_accounting.json', account)
                row.update(status=account['status'], kind=account.get('kind'),
                           block=int(receipt['blockNumber'], 16),
                           transaction_index=int(receipt['transactionIndex'], 16),
                           fee_raw=account.get('fee_raw'), provider=provider)
                summary['examined_receipts'] += 1
                if account['status']=='RECEIPT_ACCOUNTING_MATCH':
                    summary['matched_receipts'] += 1
            except Exception as exc:
                row.update(status='RECEIPT_VERIFICATION_FAILED',
                           error_type=type(exc).__name__)
                summary['receipt_errors'] += 1
            result_rows.append(row)
        save('EVENT_RECEIPT_RESULTS.json', result_rows)
        summary['receipt_selection_complete'] = len(candidates) <= args.max_receipts
        if (summary['scan_complete'] and summary['receipt_selection_complete']
                and summary['receipt_errors']==0 and summary['matched_receipts'] >= args.min_matched):
            summary['status']='BOUNDED_EVENT_SCAN_AND_SAMPLE_ACCOUNTING_PASS'
        else:
            summary['status']='INCOMPLETE_OR_UNMATCHED'
    except Exception as exc:
        summary['error_type']=type(exc).__name__
        summary['status']='FAILED'
    finally:
        if rpc is not None:
            save('RPC_FAILURE_TYPES.json',
                 dict(total=len(rpc.failures),
                      failures_by_method={k:sum(x.get('method')==k for x in rpc.failures)
                                          for k in set(x.get('method') for x in rpc.failures)}))
        save('SUMMARY.json', summary)
        save('SHA256.json', {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in out.iterdir() if p.is_file() and p.name!='SHA256.json'})
        print(json.dumps(summary, indent=2), flush=True)
    return 0 if summary['status']=='BOUNDED_EVENT_SCAN_AND_SAMPLE_ACCOUNTING_PASS' else 1


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--windows', required=True, help='explicit decimal start:end windows, comma-separated')
    p.add_argument('--out', required=True)
    p.add_argument('--chunk', type=int, default=20)
    p.add_argument('--max-rpc-calls', type=int, default=120)
    p.add_argument('--max-receipts', type=int, default=48)
    p.add_argument('--min-matched', type=int, default=2)
    args=p.parse_args()
    if min(args.chunk, args.max_rpc_calls, args.max_receipts) <= 0 or args.min_matched < 0:
        p.error('invalid limits')
    return run(args)


if __name__=='__main__':
    raise SystemExit(main())
