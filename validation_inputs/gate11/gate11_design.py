#!/usr/bin/env python3
"""Gate 11 policy-design experiment, NOT live CHAR data nor EVM execution.
Common-random-number comparisons, explicit train/holdout split, finite-grid
robust epsilon constraints. Fee formulas are real-number source replicas.
Exogenous valuations and CHAR unit price are synthetic. Receipt beneficiaries
are unidentified; no producer financing inference is made.
"""
from __future__ import annotations
import argparse, math
from pathlib import Path
import numpy as np
import pandas as pd
from gate11_optimize import fee_rule, inputs, hhi, GAS_SUCCESS, GAS_FAIL, P_TOKEN

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data';DATA.mkdir(exist_ok=True)

POLICIES=[
 'legacy','smooth_0.01','smooth_0.03','smooth_0.15',
 'clip_0.05','clip_0.075','clip_0.10','clip_0.15','clip_0.20',
 'extension_0.001','extension_0.005','extension_0.010',
 'flat_0.05','flat_0.10'
]
CAP_BUFFERS=(0.,.05,.15,.30)


def policy_fee(act,q,Q,x,policy):
    if policy.startswith('flat_'):
        return float(policy.split('_')[1])*x
    base=fee_rule(act,q,Q,x,0.)
    if policy=='legacy':return base
    if policy.startswith('smooth_'):
        return fee_rule(act,q,Q,x,float(policy.split('_')[1]))
    if policy.startswith('clip_'):
        a=float(policy.split('_')[1]);
        if Q==q:return a*x
        return min(base,a*x) if act=='D' else max(base,a*x)
    if policy.startswith('extension_'):
        floor=float(policy.split('_')[1])
        if Q==0:return .1*x  # first-deposit corner remains open
        if act=='D':return .36*x if Q==q else base
        return floor*x if Q==q else max(base,floor*x)
    raise ValueError(policy)


def audit_monotonicity():
    # Exact arithmetic mathematical design statements use Q fixed, x fixed.
    # Numeric grid checks are corroborative only; proof is in report.
    records=[]
    x=10.;Q=100.
    qs=np.r_[np.linspace(10,99,224),99.5,99.9,99.99,99.9999,100.]
    for policy in POLICIES:
        d=np.array([policy_fee('D',float(q),Q,x,policy) for q in qs]);
        r=np.array([policy_fee('R',float(q),Q,x,policy) for q in qs]);
        dmono=bool((np.diff(d)>=-1e-8).all());rmono=bool((np.diff(r)<=1e-8).all());
        errD=abs(policy_fee('D',Q-1e-6,Q,x,policy)-policy_fee('D',Q,Q,x,policy));
        errR=abs(policy_fee('R',Q-1e-6,Q,x,policy)-policy_fee('R',Q,Q,x,policy));
        # absolute accuracy of 1e-3 CHAR is suitable for this discrete numerical stress grid
        continuous_near=errD<1e-3 and errR<1e-3
        records.append(dict(policy=policy,deposit_monotone_grid=dmono,redemption_monotone_grid=rmono,
            boundary_approx_continuous=continuous_near,near_jump_deposit=errD,near_jump_redeem=errR,
            min_deposit=float(d.min()),max_deposit=float(d.max())))
    df=pd.DataFrame(records)
    df.to_csv(DATA/'monotonicity_grid_check_SYNTHETIC.csv',index=False)
    return df


def run_scenario(initial, draw, policy, cap_buffer):
    q=np.array(initial,dtype=float).copy();N=len(draw['reverse']);
    submitted=completed=fail_cap=fail_inventory=0
    volume=fees=gains=0.; deposited=redeemed=0
    for k in range(N):
        ids=[2*k,2*k+1];Q0=float(q.sum());plans={}
        for i in ids:
            j=int(draw['j'][i]);x=float(draw['x'][i]);act='D' if draw['deposit'][i] else 'R'
            if act=='R' and (q[j]<x or x>=Q0):continue
            f=policy_fee(act,float(q[j]),Q0,x,policy)
            val=float(draw['outside'][i] if act=='D' else draw['buyer'][i]);
            gross=P_TOKEN*x*((1-val) if act=='D' else (val-1))
            if gross-P_TOKEN*f-GAS_SUCCESS<0:continue
            economic_cap=max(0.,(gross-GAS_SUCCESS+GAS_FAIL)/P_TOKEN)
            m=min(f+cap_buffer,economic_cap)
            if m+1e-12<f:continue
            plans[i]=(j,x,act,gross,m)
        order=ids[::-1] if bool(draw['reverse'][k]) else ids
        for i in order:
            if i not in plans:continue
            submitted+=1
            j,x,act,gross,m=plans[i];Q=float(q.sum())
            if act=='R' and (q[j]<x or Q<=x):
                fail_inventory+=1;gains-=GAS_FAIL;continue
            f=policy_fee(act,float(q[j]),Q,x,policy)
            if f>m+1e-9:
                fail_cap+=1;gains-=GAS_FAIL;continue
            if not 0<=f<=x+1e-8:raise ValueError((policy,act,f,x))
            completed+=1; volume+=x;fees+=f;gains+=gross-GAS_SUCCESS
            q[j]+=x if act=='D' else -x
            deposited+=(act=='D');redeemed+=(act=='R')
    assert submitted==completed+fail_cap+fail_inventory
    return dict(submitted=submitted,completed=completed,volume=volume,fees=fees,gains=gains,
        hhi=hhi(q),max_share=float(max(q)/sum(q)),
        completion=completed/submitted if submitted else float('nan'),
        fail_cap=fail_cap,fail_inventory=fail_inventory,
        deposits=deposited,redemptions=redeemed)


def main(reps=40,rounds=150,seed=20261116):
    s=pd.read_csv(DATA/'public_indexed_char_snapshot.csv')['inventory_tco2'].values.astype(float)
    scenarios={'published_7project_snapshot':s,
               'near_monopoly_SYNTHETIC':np.array([100.,.1]),
               'exact_single_project_SYNTHETIC':np.array([100.,0.])}
    audits=audit_monotonicity()
    eligible=audits.loc[audits.deposit_monotone_grid & audits.redemption_monotone_grid & audits.boundary_approx_continuous,'policy'].tolist()
    # Identity and stress tests: smoothing is continuous but not monotone.
    assert 'smooth_0.01' not in eligible and 'legacy' not in eligible
    assert 'clip_0.10' in eligible and 'extension_0.001' in eligible
    rows=[]
    for sid,(name,q0) in enumerate(scenarios.items()):
        for rep in range(reps):
            draws=inputs(seed+sid*100000+rep,q0,rounds)
            for p in POLICIES:
                for b in CAP_BUFFERS:
                    val=run_scenario(q0,draws,p,b)
                    rows.append(dict(scenario=name,rep=rep,group='training' if rep<int(reps*.65) else 'holdout',
                        policy=p,cap_buffer=b,**val))
    raw=pd.DataFrame(rows);raw.to_csv(DATA/'replications_SYNTHETIC.csv',index=False)
    means=raw.groupby(['group','scenario','policy','cap_buffer'],as_index=False).agg(
        volume=('volume','mean'),completion=('completion','mean'),hhi=('hhi','mean'),
        max_share=('max_share','mean'),fees=('fees','mean'),gains=('gains','mean'),
        executed=('completed','mean'),submitted=('submitted','mean'),
        fail_cap=('fail_cap','mean'),fail_inventory=('fail_inventory','mean'))
    means.to_csv(DATA/'policy_scenario_means_SYNTHETIC.csv',index=False)
    base=means[(means.policy=='legacy') & (means.cap_buffer==.15)].set_index(['group','scenario'])
    # Synthetic normative constraints are declared ex ante, not estimated.
    # HHI should not exceed legacy by >0.020; completion must remain within 3 pp.
    # Allocate >=70% of legacy CHAR fee quantity to generic recipients.
    # Eligible throughput >=80% of baseline. C1 need NOT infer producer identity.
    candid=[]
    for p in eligible:
        for b in CAP_BUFFERS:
            g=means[(means.group=='training') & (means.policy==p)&(means.cap_buffer==b)]
            feasible=True;checks=[]; min_volume_ratio=float('inf'); min_gain_ratio=float('inf')
            for row in g.itertuples(index=False):
                ref=base.loc[('training',row.scenario)]
                okH=row.hhi<=ref.hhi+.020+1e-12
                okC=row.completion>=ref.completion-.030-1e-12
                okF=row.fees>=ref.fees*.70-1e-12
                okV=row.volume>=ref.volume*.80-1e-12
                feasible &= all((okH,okC,okF,okV))
                checks.append(f'{row.scenario}:H{int(okH)} C{int(okC)} F{int(okF)} V{int(okV)}')
                min_volume_ratio=min(min_volume_ratio,row.volume/ref.volume)
                min_gain_ratio=min(min_gain_ratio,row.gains/ref.gains)
            candid.append(dict(policy=p,cap_buffer=b,training_feasible=feasible,
                worst_case_volume_ratio=min_volume_ratio,worst_case_gains_ratio=min_gain_ratio,
                checks=';'.join(checks)))
    cand=pd.DataFrame(candid).sort_values(['training_feasible','worst_case_volume_ratio'],ascending=False)
    cand.to_csv(DATA/'epsilon_constrained_policy_grid.csv',index=False)
    feasible=cand[cand.training_feasible]
    if len(feasible):
        chosen=feasible.iloc[0][['policy','cap_buffer']].to_dict()
        policy=str(chosen['policy']);b=float(chosen['cap_buffer'])
        selected=means[(means.policy==policy)&(means.cap_buffer==b)].copy()
        selected.to_csv(DATA/'selected_policy_means_SYNTHETIC.csv',index=False)
        # Holdout eval WITHOUT reselection.
        hold=selected[selected.group=='holdout'];evalrows=[]
        for row in hold.itertuples(index=False):
            ref=base.loc[('holdout',row.scenario)]
            evalrows.append(dict(scenario=row.scenario,selected_policy=policy,cap_buffer=b,
                volume_ratio=row.volume/ref.volume,
                gains_ratio=row.gains/ref.gains,
                delta_HHI=row.hhi-ref.hhi,
                delta_completion=row.completion-ref.completion,
                fee_ratio=row.fees/ref.fees,
                holdout_constraints_pass=(row.hhi<=ref.hhi+.02 and row.completion>=ref.completion-.03 and row.fees>=.7*ref.fees and row.volume>=.8*ref.volume)))
        hold=pd.DataFrame(evalrows);hold.to_csv(DATA/'selected_holdout_SYNTHETIC.csv',index=False)
        print('chosen training policy:',chosen)
        print('holdout evaluation:'); print(hold.to_string(index=False))
    else:
        print('NO FEASIBLE POLICY on training under preset constraints')
    print('policies',len(POLICIES),'buffers',len(CAP_BUFFERS),'scenarios',len(scenarios),'reps',reps,'rounds',rounds)
    print('monotone+boundary eligible',eligible)
    print('feasible count',len(feasible),'of',len(cand))
    print('top candidates:\n',cand.head(12).to_string(index=False))
    return raw,means,cand

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--reps',type=int,default=40);a.add_argument('--rounds',type=int,default=150)
    z=a.parse_args();main(z.reps,z.rounds)
