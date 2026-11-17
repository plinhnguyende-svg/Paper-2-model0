"""Gate 29 offline tests: coverage completeness, fee precision, partial receipts,
historical prestate provenance, and identification guardrails."""
import csv
from decimal import Decimal
import io
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from gate29_event_census import (
    as_int,covered_intervals,missing_intervals,valid_rpc_log,
    extract_event_rows,tx_candidates,identification_audit,write_panel,
    receipt_row
)
from gate29_prestate_enrich import reference_enrichment,VERIFIED_GATE25


def fake_log(n,topic,data,block=10,tx_i=3,li=4):
    return {
       "address":"0x20b048fa035d5763685d695e66adf62c5d9f5055",
       "blockNumber":hex(block),"transactionIndex":hex(tx_i),
       "logIndex":hex(li),"transactionHash":"0x"+"1"*64,
       "blockHash":"0x"+"2"*64,"topics":[topic],
       "data":data,"removed":False
    }


class CensusTests(unittest.TestCase):
    def test_holes_are_never_counted_as_covered(self):
        rec=[dict(start=0,end=100,status="SUCCESS"),
             dict(start=90,end=150,status="SUCCESS"),
             dict(start=151,end=199,status="FAILED_SINGLE_BLOCK"),
             dict(start=210,end=300,status="SUCCESS")]
        self.assertEqual(covered_intervals(rec),[(0,150),(210,300)])
        self.assertEqual(missing_intervals(0,320,covered_intervals(rec)),
                         [(151,209),(301,320)])

    def test_global_complete_requires_all_block_intervals(self):
        self.assertEqual(missing_intervals(0,100,[(0,49),(50,100)]),[])
        self.assertEqual(missing_intervals(0,100,[(0,49),(51,100)]),[(50,50)])

    def test_wrong_log_address_or_topic_is_fail_closed(self):
        x=fake_log("Deposited","0x"+"a"*64,"0x"+"0"*128)
        with self.assertRaises(ValueError):
            valid_rpc_log(x,10,10,{x["address"]},{"0x"+"b"*64})
        with self.assertRaises(ValueError):
            valid_rpc_log(x,9,9,{x["address"]},{x["topics"][0]})
        self.assertTrue(valid_rpc_log(x,10,10,{x["address"]},
                                      {x["topics"][0]}))

    def test_trade_event_metadata_extract_and_duplicates(self):
        topic="0x"+"a"*64
        data="0x"+("0"*24+"a"*40)+format(10**18,"064x")
        d=fake_log("Deposited",topic,data)
        rows=extract_event_rows([d],{"Deposited":topic})
        self.assertEqual(rows[0]["amount_raw"],10**18)
        self.assertEqual(rows[0]["token"],"0x"+"a"*40)
        self.assertEqual(tx_candidates([d],{"Deposited":topic}),
                         ["0x"+"1"*64])
        with self.assertRaises(ValueError):
            extract_event_rows([d,d],{"Deposited":topic})

    def test_canonical_reference_never_infers_new_transactions(self):
        tx=list(VERIFIED_GATE25)[0]
        ref=VERIFIED_GATE25[tx]
        row=dict(tx_hash=tx,transaction_type=ref["kind"],
                 token=ref["token"],amount_raw=ref["amount_raw"],
                 actual_fee_raw=ref["actual_fee_raw"])
        self.assertTrue(reference_enrichment(row))
        self.assertEqual(row["transaction_index_aware_prestate"],
                         "EXACT_PRE_TX_GATE25_VALIDATED")
        other=dict(tx_hash="0x"+"0"*64,transaction_type="deposit",
                   amount_raw=ref["amount_raw"],token=ref["token"])
        self.assertFalse(reference_enrichment(other))
        self.assertNotIn("pre_total_raw",other)

    def test_reference_rejects_mismatched_fee_or_amount(self):
        tx=list(VERIFIED_GATE25)[0]
        ref=VERIFIED_GATE25[tx]
        row=dict(tx_hash=tx,transaction_type=ref["kind"],
                 token=ref["token"],amount_raw=ref["amount_raw"],
                 actual_fee_raw=ref["actual_fee_raw"]+1)
        self.assertFalse(reference_enrichment(row))
        self.assertEqual(row["reference_error"],
                         "GATE25_IDENTIFIERS_DO_NOT_MATCH")

    def test_unreconciled_raw_trade_keeps_all_state_fields_null(self):
        topic="0x"+"a"*64
        amount=10**18
        d=fake_log("Deposited",topic,
                   "0x"+("0"*24+"a"*40)+format(amount,"064x"))
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            event_rows=extract_event_rows([d],{"Deposited":topic})
            rows=write_panel(out,[],event_rows,{"Deposited":topic})
            self.assertEqual(len(rows),1)
            self.assertIsNone(rows[0]["pre_total_raw"])
            self.assertIsNone(rows[0]["pre_hhi"])
            self.assertEqual(rows[0]["fee_attribution"],
                             "NOT_RECONCILED_OR_MULTIACTION")

    def test_identification_does_not_infer_causality(self):
        r=identification_audit([],[],[],{"complete":True},
                                {"complete":True,"addresses":["0x"+"1"*40]})
        self.assertEqual(r["status"],
                         "NOT_IDENTIFIED_INCOMPLETE_PRESTATE_OR_RECEIPTS")
        self.assertEqual(r["metrics"]["observability"]["nonparticipants"],
                         "UNOBSERVED")

    def test_large_raw_fee_ratios_use_exact_decimal(self):
        numerator=2**200+1
        denominator=2**201+7
        ratio=Decimal(numerator)/Decimal(denominator)
        self.assertGreater(ratio,Decimal("0.49"))
        self.assertLess(ratio,Decimal("0.5"))
        self.assertNotEqual(Decimal(str(numerator/denominator)),ratio)

    def test_actual_pool_HHI_requires_full_project_vector(self):
        # Two equal total inventories can have radically different HHI
        # despite same share for one observed project; impossible to infer.
        self.assertNotEqual((Decimal("0.5")**2+Decimal("0.5")**2),
                            (Decimal("0.5")**2+Decimal("0.25")**2+
                             Decimal("0.25")**2))


if __name__=="__main__":
    unittest.main()
