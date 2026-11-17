"""Offline synthetic tests for Gate 24; no mainnet evidence inferred."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from audit_char_event_windows import (parse_windows, validate_log,
                                       scan_window, ordered_candidates,
                                       canonical_receipt)
from char_receipt_accounting import POOL

TOPIC='0x'+'1'*64
HASH='0x'+'a'*64
BLOCK_HASH='0x'+'b'*64


def synthetic_log(height, tx=HASH):
    return dict(address=POOL, blockNumber=hex(height), transactionIndex='0x0',
                logIndex='0x0', topics=[TOPIC], transactionHash=tx,
                blockHash=BLOCK_HASH, data='0x', removed=False)


class SplitRPC:
    def __init__(self):
        self.queries=[]
    def call(self,method,params):
        self.queries.append((method,params))
        lo=int(params[0]['fromBlock'],16);hi=int(params[0]['toBlock'],16)
        if hi-lo+1>2:
            raise RuntimeError('provider block-range limit')
        return [synthetic_log(x) for x in range(lo,hi+1)],'mock'


class CanonicalRPC:
    def __init__(self, good=True):
        self.good=good
    def call(self,method,params):
        tx={'hash':HASH, 'blockHash':BLOCK_HASH, 'transactionIndex':'0x0'}
        receipt=dict(transactionHash=HASH, blockHash=BLOCK_HASH,
                     transactionIndex='0x0', blockNumber='0x10',status='0x1',
                     logs=[synthetic_log(16)] if self.good else [])
        block={'hash':BLOCK_HASH,'transactions':[HASH]}
        return {'eth_getTransactionByHash':tx,
                'eth_getTransactionReceipt':receipt,
                'eth_getBlockByNumber':block}[method], 'mock'


class EventWindowTests(unittest.TestCase):
    def test_windows_sort_and_overlap_rejected(self):
        self.assertEqual(parse_windows('20:25,1:10'),[(1,10),(20,25)])
        for bad in ['1:2,2:4','5:4','bad','1','-1:9']:
            with self.subTest(raw=bad),self.assertRaises(ValueError):
                parse_windows(bad)

    def test_adaptive_split_exhausts_every_block(self):
        rpc=SplitRPC();ledger=[];found=[]
        scan_window(rpc,10,15,{TOPIC},dict(used=0,limit=20),ledger,found)
        self.assertEqual([int(x['blockNumber'],16) for x in found],list(range(10,16)))
        successes=[r for r in ledger if r['status']=='SCANNED']
        self.assertEqual(sum(r['end']-r['start']+1 for r in successes),6)
        self.assertTrue(all(r['status']=='SCANNED' for r in ledger))

    def test_budget_does_not_fake_completeness(self):
        ledger=[];found=[]
        scan_window(SplitRPC(),10,15,{TOPIC},dict(used=0,limit=1),ledger,found)
        self.assertTrue(any(row['status']=='UNSCANNED_RPC_BUDGET' for row in ledger))
        self.assertFalse(found)

    def test_reject_wrong_contract_and_block(self):
        for bad in [dict(synthetic_log(11),address='0x'+'c'*40),
                    synthetic_log(12),dict(synthetic_log(11),removed=True)]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                validate_log(bad,10,11,{TOPIC})

    def test_candidates_deduplicate(self):
        logs=[dict(synthetic_log(11),logIndex='0x1'),synthetic_log(11)]
        self.assertEqual(ordered_candidates(logs),[HASH])

    def test_canonical_receipt_requires_discovered_event(self):
        self.assertEqual(canonical_receipt(CanonicalRPC(),HASH,[synthetic_log(16)])[3],'mock')
        with self.assertRaises(ValueError):
            canonical_receipt(CanonicalRPC(False),HASH,[synthetic_log(16)])


if __name__ == '__main__':
    unittest.main()
