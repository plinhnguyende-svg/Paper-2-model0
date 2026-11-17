"""Narrow raw-receipt accounting. No formula, identity or cash-financing inference."""
POOL='0x20b048fa035d5763685d695e66adf62c5d9f5055'
TRANSFER='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
ZERO='0x'+'0'*40


def decode_words(data):
    if not data.startswith('0x') or (len(data)-2)%64:
        raise ValueError('invalid static ABI data')
    return [data[i:i+64] for i in range(2,len(data),64)]


def token_transfers(receipt):
    rows=[]
    for l in receipt.get('logs',[]):
        t=l.get('topics',[])
        if len(t)==3 and t[0].lower()==TRANSFER and len(l.get('data',''))==66:
            rows.append(dict(token=l['address'].lower(),sender='0x'+t[1][-40:].lower(),
                             recipient='0x'+t[2][-40:].lower(),amount_raw=int(l['data'],16),
                             log_index=int(l['logIndex'],16)))
    return rows


def reconcile(receipt,topics):
    events={name:[] for name in topics}
    for l in receipt.get('logs',[]):
        if l['address'].lower()!=POOL or len(l.get('topics',[]))!=1:continue
        for name,topic in topics.items():
            if l['topics'][0].lower()!=topic.lower():continue
            words=decode_words(l['data'])
            n=3 if name=='Redeemed' else 2
            if len(words)!=n:raise ValueError('unsupported event layout')
            events[name].append(words)
    flows=token_transfers(receipt)
    pool=[r for r in flows if r['token']==POOL]
    result=dict(status='UNSUPPORTED_OR_NON_FEE_ACTION',checks={},events=events,
                token_transfers=flows,scope='receipt event/transfer accounting only; no prestate or producer identity')
    if len(events['DepositFeePaid'])==1 and len(events['Deposited'])==1 and not events['Redeemed']:
        fee_words=events['DepositFeePaid'][0];dep=events['Deposited'][0]
        actor='0x'+fee_words[0][-40:].lower();token='0x'+dep[0][-40:].lower()
        fee=int(fee_words[1],16);amount=int(dep[1],16)
        minted=[r for r in pool if r['sender']==ZERO]
        result.update(kind='deposit',actor=actor,underlying=token,amount_raw=amount,fee_raw=fee,
                      observed_fee_destinations=[r for r in minted if r['recipient']!=actor])
        result['checks']=dict(
            total_pool_mint_equals_underlying=sum(r['amount_raw'] for r in minted)==amount,
            actor_mint_equals_amount_minus_fee=sum(r['amount_raw'] for r in minted if r['recipient']==actor)==amount-fee,
            other_mints_equal_fee=sum(r['amount_raw'] for r in minted if r['recipient']!=actor)==fee,
            underlying_enters_pool=sum(r['amount_raw'] for r in flows if r['token']==token and r['sender']==actor and r['recipient']==POOL)==amount)
        result['ambiguity']='self-recipient or multi-call flows can prevent this narrow match; never force attribution'
    elif len(events['Redeemed'])==1 and events['RedeemFeePaid'] and not events['Deposited']:
        red=events['Redeemed'][0];actor='0x'+red[0][-40:].lower();token='0x'+red[1][-40:].lower();amount=int(red[2],16)
        fee_events=events['RedeemFeePaid']+events['RedeemFeeBurnt']
        same_actor=all('0x'+w[0][-40:].lower()==actor for w in fee_events)
        fee=sum(int(w[1],16) for w in fee_events)
        fee_flows=[r for r in pool if r['sender']==actor and r['recipient']!=ZERO]
        result.update(kind='redemption',actor=actor,underlying=token,amount_raw=amount,fee_raw=fee,
                      observed_fee_destinations=fee_flows)
        result['checks']=dict(
            fee_events_same_actor=same_actor,
            pool_burn_equals_underlying=sum(r['amount_raw'] for r in pool if r['sender']==actor and r['recipient']==ZERO)==amount,
            net_and_burn_fee_events_equal_token_flows=sum(r['amount_raw'] for r in fee_flows)==fee,
            fee_event_amount_multiset_matches=sorted(int(w[1],16) for w in fee_events)==sorted(r['amount_raw'] for r in fee_flows),
            underlying_leaves_pool=sum(r['amount_raw'] for r in flows if r['token']==token and r['sender']==POOL and r['recipient']==actor)==amount)
    if result['checks']:
        result['status']='RECEIPT_ACCOUNTING_MATCH' if all(result['checks'].values()) else 'NOT_MATCHED_OR_AMBIGUOUS'
    return result
