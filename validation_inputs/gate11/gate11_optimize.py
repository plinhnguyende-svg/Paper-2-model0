#!/usr/bin/env python3
"""Gate 11 reproducible *synthetic* economic design optimization.

This is NOT EVM, not observed transaction data, not calibrated producer economics.
Uses real-number Toucan source formulas for interior fees, with Decimal near
redemption boundary; ignores caps, seeding, exact EVM rounding and access rights.
No producer wallet attribution: allocated fee tokens are generic recipients.
"""
from __future__ import annotations
import argparse, itertools, math
from decimal import Decimal, localcontext
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
P_TOKEN=200.0 # arbitrary synthetic unit-of-account for toy valuation; NOT observed CHAR price
GAS_SUCCESS=3.0
GAS_FAIL=2.0


def fee_rule(action: str, project_balance: float, pool_balance: float, amount: float, tau: float) -> float:
    """Real-valued reference with 10% single-asset branch and smoothing τ.
    τ=0 means legacy reference. An isolated zero-balance pool uses flat 10%.
    The source implementation can revert if positive mathematical fee rounds to 0.
    """
    q,Q,x=project_balance,pool_balance,amount
    assert 0 <= q <= Q + 1e-9 and x>0
    assert action in ('D','R')
    if action=='R':
        assert x<=q and x<Q
    if Q==q:
        source=.1*x
    elif action=='D':
        a=q/Q; b=(q+x)/(Q+x)
        source=.18*(q*math.log10(1-.99*a)-(q+x)*math.log10(1-.99*b))
    else:
        if (Q-q)/Q < 1e-4:
            with localcontext() as ctx:
                ctx.prec=65
                dq=Decimal(str(q));dQ=Decimal(str(Q));dx=Decimal(str(x));
                a=dq/dQ;b=(dq-dx)/(dQ-dx)
                source=float(Decimal('.30')*((dq-dx)*(b+Decimal('.1')).log10()-dq*(a+Decimal('.1')).log10()+dx*Decimal('1.1').log10()))
        else:
            a=q/Q;b=(q-x)/(Q-x)
            source=.30*((q-x)*math.log10(b+.1)-q*math.log10(a+.1)+x*math.log10(1.1))
        if source<0:source=.3*x # source fallback; don't interpret negative as exact EVM
    if tau==0 or Q==0:return max(0.0,source)
    other=max(0.0,Q-q)
    weight=other/(other+tau*Q)
    smoothed=(1-weight)*.1*x+weight*source
    return max(0.,smoothed)


def hhi(q):
    Q=float(np.sum(q))
    return float(np.sum(np.square(q/Q))) if Q>0 else float('nan')


def inputs(seed, initial, rounds):
    rng=np.random.default_rng(seed)
    n=len(initial)
    prob=.45*np.asarray(initial)/sum(initial)+.55*np.full(n,1/n)
    N=2*rounds
    return {
        'j':rng.choice(n,N,p=prob),
        'deposit':rng.random(N)<.55,
        'x':rng.uniform(1.,10.,N),
        'outside':rng.uniform(.75,1.05,N),
        'buyer':rng.uniform(.98,1.35,N),
        'reverse':rng.random(rounds)<.5,
    }


def run_one(initial, draw, tau, buffer):
    q=np.array(initial,dtype=float).copy()
    submitted=completed=cap_fail=inventory_fail=0
    volume=0.;fee_tokens=0.;net_trade_surplus=0.; n_D=n_R=0
    rounds=len(draw['reverse'])
    for r in range(rounds):
        ids=[2*r,2*r+1]; startQ=float(q.sum())
        plans={}
        for i in ids:
            j=int(draw['j'][i]);x=float(draw['x'][i]);act='D' if draw['deposit'][i] else 'R'
            if act=='R' and (x>q[j] or x>=startQ):continue
            f=fee_rule(act,float(q[j]),startQ,x,tau)
            val=float(draw['outside'][i] if act=='D' else draw['buyer'][i])
            gross=P_TOKEN*x*((1-val) if act=='D' else (val-1))
            # Quote-level private IR before submission; recipient identities not assumed.
            if gross-P_TOKEN*f-GAS_SUCCESS<0:continue
            # Cap is ex post rational conditional on sunk failed-execution gas.
            economic_cap=max(0.,(gross-GAS_SUCCESS+GAS_FAIL)/P_TOKEN)
            cap=min(f+buffer,economic_cap)
            if cap+1e-12<f:continue
            plans[i]=(j,x,act,cap,gross)
        order=ids[::-1] if draw['reverse'][r] else ids
        for i in order:
            if i not in plans:continue
            submitted+=1
            j,x,act,cap,gross=plans[i]
            Q=float(q.sum())
            if act=='R' and (x>q[j] or x>=Q):
                inventory_fail+=1;net_trade_surplus-=GAS_FAIL;continue
            f=fee_rule(act,float(q[j]),Q,x,tau)
            if f>cap+1e-9:
                cap_fail+=1;net_trade_surplus-=GAS_FAIL;continue
            # Validity: nonzero fee may still fail in Solidity; not modeled.
            if f<0 or f>x+1e-8:raise AssertionError(('fee violates amount',f,x))
            completed+=1;volume+=x;fee_tokens+=f
            net_trade_surplus+=gross-GAS_SUCCESS # fee transfers deliberately excluded
            q[j]+=x if act=='D' else -x
            n_D+=(act=='D');n_R+=(act=='R')
    assert submitted==completed+cap_fail+inventory_fail
    assert all(q>=-1e-6)
    return {'submitted':submitted,'completed':completed,'fail_fee_cap':cap_fail,
        'fail_inventory':inventory_fail,'executed_tco2':volume,'fee_tokens_CHAR':fee_tokens,
        'trade_gains_less_gas_USD_MODEL':net_trade_surplus,'hhi_final':hhi(q),
        'max_project_share':max(q)/sum(q),'deposits':n_D,'redemptions':n_R,
        'completion_given_submit':completed/submitted if submitted else float('nan')}


def optimize(replications=35, rounds=150, seed=20261116):
    snapshot=pd.read_csv(DATA/'public_indexed_char_snapshot.csv')
    init=snapshot['inventory_tco2'].to_numpy(float)
    scenarios={'published_7project_snapshot':init,
               'near_monopoly_SYNTHETIC':np.array([100.,0.1]),
               'single_project_SYNTHETIC':np.array([100.,0.])}
    # Precommitted feasible policy grid; no continuous-optimum or EVM claim.
    tau_grid=(0.,.003,.01,.02,.03,.07,.15)
    buffer_grid=(0.,.05,.15,.30,.60)
    policies=list(itertools.product(tau_grid,buffer_grid))
    rows=[]
    for scenario_id,(sname,initial) in enumerate(scenarios.items()):
        for rep in range(replications):
            draw=inputs(seed+scenario_id*100000+rep,initial,rounds)
            for tau,b in policies:
                results=run_one(initial,draw,tau,b)
                rows.append(dict(scenario=sname,seed=rep,tau=tau,buffer=b,**results))
    df=pd.DataFrame(rows)
    df.to_csv(DATA/'simulated_replications_SYNTHETIC.csv',index=False)
    agg=df.groupby(['scenario','tau','buffer'],as_index=False).agg(
        volume=('executed_tco2','mean'),completion=('completion_given_submit','mean'),
        final_hhi=('hhi_final','mean'),max_project_share=('max_project_share','mean'),
        fees=('fee_tokens_CHAR','mean'),gains=('trade_gains_less_gas_USD_MODEL','mean'),
        completed=('completed','mean'),submitted=('submitted','mean'),
        fail_cap=('fail_fee_cap','mean'),fail_inv=('fail_inventory','mean'))
    agg.to_csv(DATA/'scenario_policy_means_SYNTHETIC.csv',index=False)
    bases=agg[(agg.tau==0)&(agg.buffer==.15)].set_index('scenario')
    # Explicit epsilon-constraint policy experiment; all bounds relative to published-source baseline.
    # Gross trade gains exclude fees transferred to recipients, avoiding double counting.
    paired=[]
    for (tau,b),g in agg.groupby(['tau','buffer']):
        feasible=True;reasons=[];worst_ratio=float('inf');avg_gains=[];avg_volume=[]
        for _,row in g.iterrows():
            base=bases.loc[row.scenario]
            h_ok=row.final_hhi<=base.final_hhi+.015+1e-10
            comp_ok=row.completion>=base.completion-.02-1e-10
            fees_ok=row.fees>=.85*base.fees-1e-10
            volume_ok=row.volume>=.90*base.volume-1e-10
            if not all((h_ok,comp_ok,fees_ok,volume_ok)):
                feasible=False
                reasons.append(f'{row.scenario}: HHI={h_ok},completion={comp_ok},fees={fees_ok},volume={volume_ok}')
            worst_ratio=min(worst_ratio,row.gains/max(1e-12,float(base.gains)))
            avg_gains.append(float(row.gains));avg_volume.append(float(row.volume))
        paired.append(dict(tau=tau,buffer=b,feasible=feasible,
            worst_normalized_net_trade_gains=worst_ratio,
            mean_net_trade_gains_model=np.mean(avg_gains),
            mean_volume=np.mean(avg_volume),fail_constraints='; '.join(reasons)))
    rank=pd.DataFrame(paired).sort_values(['feasible','worst_normalized_net_trade_gains','mean_volume'],ascending=[False,False,False])
    rank.to_csv(DATA/'robust_policy_rank_SYNTHETIC.csv',index=False)
    best=rank[rank.feasible].iloc[0]
    selected=agg[(agg.tau==best.tau)&(agg.buffer==best.buffer)].copy()
    selected.to_csv(DATA/'chosen_policy_scenarios_SYNTHETIC.csv',index=False)
    baseline=agg[(agg.tau==0)&(agg.buffer==.15)].copy()
    baseline.to_csv(DATA/'baseline_policy_scenarios_SYNTHETIC.csv',index=False)
    print('n_scenarios',len(scenarios),'policies',len(policies),'replications',replications,'rounds',rounds)
    print('n feasible policies',int(rank.feasible.sum()))
    print('CHOSEN',best[['tau','buffer','worst_normalized_net_trade_gains','mean_volume']].to_dict())
    print('\nSELECTED:\n',selected.to_string(index=False))
    print('\nBASELINE:\n',baseline.to_string(index=False))
    return df,agg,rank


def test_fee_invariants():
    assert fee_rule('D',100,100,10,0)==1
    assert fee_rule('R',100,100,10,0)==1
    assert abs(fee_rule('D',100,100+.0001,10,0)-3.6)<1e-3
    assert 0<=fee_rule('R',100,100+.0001,10,0)<1e-7
    assert abs(fee_rule('D',100,100+.0001,10,.01)-1)<.001
    assert abs(fee_rule('R',100,100+.0001,10,.01)-1)<.001
    for tau in [0.,.003,.01,.07]:
        for q,Q in [(0,100),(25,100),(50,100),(99.9,100),(100,100)]:
            for x in [1.,10.]:
                assert 0<=fee_rule('D',q,Q,x,tau)<=x
                if q>=x and x<Q:
                    assert 0<=fee_rule('R',q,Q,x,tau)<=x
    print('PASS: deterministic real-valued fee invariants (NOT EVM)')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replications',type=int,default=35);p.add_argument('--rounds',type=int,default=150)
    a=p.parse_args();test_fee_invariants();optimize(a.replications,a.rounds)
