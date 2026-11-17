"""Synthetic ABI fixtures test the parser, never presented as on-chain evidence."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from char_receipt_accounting import POOL,TRANSFER,ZERO,decode_words,reconcile

ACTOR='0x'+'a'*40;R1='0x'+'b'*40;R2='0x'+'c'*40;ASSET='0x'+'d'*40;BURN='0x'+'e'*40
NAMES=['DepositFeePaid','RedeemFeePaid','RedeemFeeBurnt','Deposited','Redeemed']
TOPICS={name:'0x'+format(i+1,'064x') for i,name in enumerate(NAMES)}


def word(v):return v[2:].rjust(64,'0') if isinstance(v,str) else format(v,'064x')
def event(name,*values):return dict(address=POOL,topics=[TOPICS[name]],data='0x'+''.join(word(v) for v in values))
def transfer(token,sender,recipient,amount):
    return dict(address=token,topics=[TRANSFER,'0x'+word(sender),'0x'+word(recipient)],data='0x'+word(amount))
def receipt(logs):
    return dict(logs=[dict(l,logIndex=hex(i)) for i,l in enumerate(logs)])
def deposit_logs():
    return [event('DepositFeePaid',ACTOR,10),event('Deposited',ASSET,100),
            transfer(POOL,ZERO,ACTOR,90),transfer(POOL,ZERO,R1,7),transfer(POOL,ZERO,R2,3),
            transfer(ASSET,ACTOR,POOL,100)]


class ReceiptAccounting(unittest.TestCase):
    def test_deposit_fee_and_underlying_match(self):
        r=reconcile(receipt(deposit_logs()),TOPICS)
        self.assertEqual(r['status'],'RECEIPT_ACCOUNTING_MATCH');self.assertEqual(r['fee_raw'],10)

    def test_wrong_fee_mint_rejected(self):
        logs=deposit_logs();logs[3]=transfer(POOL,ZERO,R1,8)
        self.assertEqual(reconcile(receipt(logs),TOPICS)['status'],'NOT_MATCHED_OR_AMBIGUOUS')

    def test_self_recipient_not_silently_attributed(self):
        logs=deposit_logs();logs[3]=transfer(POOL,ZERO,ACTOR,7)
        self.assertEqual(reconcile(receipt(logs),TOPICS)['status'],'NOT_MATCHED_OR_AMBIGUOUS')

    def test_redemption_includes_fee_burn_address(self):
        logs=[event('Redeemed',ACTOR,ASSET,100),event('RedeemFeePaid',ACTOR,7),
              event('RedeemFeePaid',ACTOR,2),event('RedeemFeeBurnt',ACTOR,1),
              transfer(POOL,ACTOR,ZERO,100),transfer(POOL,ACTOR,R1,7),
              transfer(POOL,ACTOR,R2,2),transfer(POOL,ACTOR,BURN,1),transfer(ASSET,POOL,ACTOR,100)]
        r=reconcile(receipt(logs),TOPICS)
        self.assertEqual(r['status'],'RECEIPT_ACCOUNTING_MATCH');self.assertEqual(r['fee_raw'],10)

    def test_missing_burn_transfer_fails(self):
        logs=[event('Redeemed',ACTOR,ASSET,100),event('RedeemFeePaid',ACTOR,9),event('RedeemFeeBurnt',ACTOR,1),
              transfer(POOL,ACTOR,ZERO,100),transfer(POOL,ACTOR,R1,9),transfer(ASSET,POOL,ACTOR,100)]
        self.assertEqual(reconcile(receipt(logs),TOPICS)['status'],'NOT_MATCHED_OR_AMBIGUOUS')

    def test_mixed_actions_not_treated_as_simple_deposit(self):
        r=reconcile(receipt(deposit_logs()+[event('Redeemed',ACTOR,ASSET,1)]),TOPICS)
        self.assertEqual(r['status'],'UNSUPPORTED_OR_NON_FEE_ACTION')

    def test_wrong_contract_event_does_not_count(self):
        logs=deposit_logs();logs[0]['address']=ASSET
        self.assertEqual(reconcile(receipt(logs),TOPICS)['status'],'UNSUPPORTED_OR_NON_FEE_ACTION')

    def test_malformed_abi_is_rejected(self):
        with self.assertRaises(ValueError):decode_words('0x123')


if __name__=='__main__':unittest.main()
