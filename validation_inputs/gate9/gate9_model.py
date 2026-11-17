"""Gate 9: formal CHAR fee mechanism experiments.
Public reference: ToucanProtocol/dynamic-fee-pools FeeCalculator.sol (source baseline),
ToucanProtocol/contracts contracts/pools/Pool.sol, PoolWithFeeCalculatorERC20.sol.
All arrivals/valuations/price/gas/shocks are synthetic assumptions, NOT CHAR transactions.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import argparse
import csv
import json
import math
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / 'public_indexed_char_snapshot.csv'

@dataclass(frozen=True)
class ModelParams:
    deposit_scale: float = 0.18
    deposit_ratio: float = 0.99
    redeem_scale: float = 0.30
    redeem_shift: float = 0.10
    single_deposit: float = 0.10
    single_redeem: float = 0.10
    dust_redeem: float = 0.30

PAR = ModelParams()

def _valid(q: float, Q: float, x: float, action: str) -> None:
    if q < 0 or Q < 0 or x <= 0 or q > Q + 1e-9:
        raise ValueError('Invalid nonnegative pool state or requested amount')
    if action == 'redeem' and (x > q + 1e-9 or x >= Q - 1e-10):
        raise ValueError('Redemption must leave positive pool total in these experiments')

def dynamic_deposit_fee(q: float, Q: float, x: float, p: ModelParams = PAR) -> float:
    """Float-level replica of published 2024 FeeCalculator mathematical formula.
    Not deployed bytecode/EVM fixed-point execution; no seeding, caps, exemptions, rounding.
    """
    _valid(q,Q,x,'deposit')
    if Q == q: # exactly one project, or empty, in Solidity code
        return p.single_deposit*x
    a = q/Q
    b = (q+x)/(Q+x)
    ans = p.deposit_scale*(q*math.log10(1-p.deposit_ratio*a)
            -(q+x)*math.log10(1-p.deposit_ratio*b))
    return max(0.0,ans)

def dynamic_redeem_fee(q: float, Q: float, x: float, p: ModelParams = PAR) -> float:
    """Float-level replica; implements documented negative-number dust fallback."""
    _valid(q,Q,x,'redeem')
    if Q == q:
        return p.single_redeem*x
    a=q/Q
    b=(q-x)/(Q-x)
    raw=p.redeem_scale*((q-x)*math.log10(b+p.redeem_shift)
            -q*math.log10(a+p.redeem_shift)
            +x*math.log10(1+p.redeem_shift))
    return p.dust_redeem*x if raw < 0 else raw

def fee_for(action: str, q: float, Q: float, x: float, rule: str) -> float:
    if rule == 'dynamic':
        return dynamic_deposit_fee(q,Q,x) if action == 'deposit' else dynamic_redeem_fee(q,Q,x)
    if rule == 'flat5':
        return .05*x
    if rule == 'zero':
        return 0.0
    raise ValueError(rule)

def hhi(q: np.ndarray) -> float:
    Q = float(np.sum(q))
    return float(np.sum((q / Q)**2)) if Q>0 else float('nan')

def read_snapshot():
    d=pd.read_csv(SNAPSHOT)
    return d['project_name'].tolist(), d['inventory_tco2'].to_numpy(float)

def write_boundary(output_dir:Path):
    records=[]
    for epsilon in [0., 1., 0.1, .01, .001]:
        Q=100.+epsilon
        q=100.
        fees_r=dynamic_redeem_fee(q,Q,10.)
        fees_d=dynamic_deposit_fee(q,Q,10.)
        new_project_deposit_fee=(dynamic_deposit_fee(0,100.,epsilon) if epsilon>0 else 0)
        records.append(dict(other_project_inventory=epsilon, dominant_inventory=q,
            redemption_amount=10., redeem_fee_char=fees_r,redeem_rate=fees_r/10.,
            dominant_deposit_fee_char=fees_d, dominant_deposit_rate=fees_d/10.,
            deposit_epsilon_other_project_fee_char=new_project_deposit_fee))
    pd.DataFrame(records).to_csv(output_dir/'boundary_experiment.csv',index=False)

    projects,q=read_snapshot();Q=float(q.sum()); H=hhi(q)
    records=[]
    for j,name in enumerate(projects):
        x=10.
        q_after=q.copy();q_after[j]+=x
        delta_d=hhi(q_after)-H
        q_after=q.copy();q_after[j]-=x
        delta_r=hhi(q_after)-H
        records.append(dict(project=name,inventory=q[j],share=q[j]/Q,
            deposit_fee_char=dynamic_deposit_fee(float(q[j]),Q,x),
            redeem_fee_char=dynamic_redeem_fee(float(q[j]),Q,x),
            deposit_HHI_delta=delta_d,redeem_HHI_delta=delta_r))
    pd.DataFrame(records).to_csv(output_dir/'snapshot_one_trade.csv',index=False)
    return Q,H

def decision_gross(action:str,x:float,fee:float,ratio:float,price:float,recapture:float=0.)->float:
    """Gross surplus before gas; ratio is outside TCO2 value / CHAR price if seller,
    credit valuation / CHAR price if redeemer. Recapture alpha is hypothetical.
    """
    if action=='deposit': return price*(x-(1-recapture)*fee-ratio*x)
    return price*(ratio*x-x-(1-recapture)*fee)

def simulate_policy(rng_seed=20261116,replications=160,arrivals=650,price=200.,gas=3.,
                    supplier_outside=(.76,1.04),buyer_value=(1.0,1.36),initial_weight=.5):
    projects, initial=read_snapshot(); n=len(projects); init_prob=initial/initial.sum()
    results=[]
    for rep in range(replications):
        rng=np.random.default_rng(rng_seed+rep)
        # Generate ONE common set of arrivals for all fee-policy counterfactuals.
        project_idx=rng.choice(n,arrivals,p=initial_weight*init_prob+(1-initial_weight)*np.ones(n)/n)
        is_deposit=rng.random(arrivals)<.55
        size=rng.uniform(1.,11.,arrivals)
        outside_ratio=rng.uniform(*supplier_outside,arrivals)
        buyer_ratio=rng.uniform(*buyer_value,arrivals)
        for rule in ['dynamic','flat5','zero']:
            q=initial.copy()
            attempt=0; deposits=0; redeems=0; total_quantity=0.; fees_d=0.;fees_r=0.
            for t in range(arrivals):
                j=int(project_idx[t]); x=float(size[t]); action='deposit' if is_deposit[t] else 'redeem'
                if action=='redeem' and (q[j]<x or q.sum()-x<=0):continue
                f=fee_for(action,float(q[j]),float(q.sum()),x,rule)
                ratio=float(outside_ratio[t] if action=='deposit' else buyer_ratio[t])
                gross=decision_gross(action,x,f,ratio,price)
                if gross-gas < 0: continue
                attempt+=1
                if action=='deposit': q[j]+=x;deposits+=1;fees_d+=f
                else: q[j]-=x;redeems+=1;fees_r+=f
                total_quantity+=x
            results.append(dict(rep=rep,rule=rule,arrivals=arrivals,accepted=attempt,
                deposit_count=deposits,redeem_count=redeems,executed_volume=total_quantity,
                HHI=hhi(q),diversity=1-hhi(q),Q_end=q.sum(),fee_to_recipients_CHAR=fees_d+fees_r,
                deposit_fees_CHAR=fees_d,redeem_fees_CHAR=fees_r))
    return pd.DataFrame(results)

def slippage_stress(trials=40000,price=200.,g_success=3.,g_fail=2.,seed=20261117):
    """Independent quoted transactions based on *unanchored* public inventory snapshot.
    Exogenous one-transaction state shock occurs before own inclusion. No mempool claim.
    """
    names,initial=read_snapshot();n=len(names); Q=float(initial.sum());prob=.5*initial/Q+.5*np.ones(n)/n
    rng=np.random.default_rng(seed)
    buffers=[0.,.05,.25,.75]
    rows=[]
    for t in range(trials):
        j=int(rng.choice(n,p=prob)); action='deposit' if rng.random()<.55 else 'redeem'
        x=float(rng.uniform(1.,12.))
        ratio=float(rng.uniform(.76,1.06) if action=='deposit' else rng.uniform(1.0,1.38))
        quote=fee_for(action,float(initial[j]),Q,x,'dynamic')
        quote_gross=decision_gross(action,x,quote,ratio,price)
        submit=(quote_gross>=g_success)
        new=initial.copy()
        if rng.random()<.8:
            k=int(rng.choice(n,p=prob)); shock_x=float(rng.uniform(5.,110.))
            if rng.random()<.6: new[k]+=shock_x
            else: new[k]-=min(shock_x, .8*new[k])
        invalid_inventory=(action=='redeem' and (new[j] < x or new.sum()<=x))
        fee_exec=(float('nan') if invalid_inventory else
                  fee_for(action,float(new[j]),float(new.sum()),x,'dynamic'))
        for buffer in buffers+['break_even']:
            if isinstance(buffer,str):
                # Optimal cap under constant price, gross trading benefit linear in fee.
                maxfee=x*(1-ratio) if action=='deposit' else x*(ratio-1)
                maxfee-=(g_success-g_fail)/price
                label='break_even_cap'
            else:
                maxfee=quote+buffer
                label='buffer_'+str(buffer)
            if not submit:
                accepted=False;net=0.;failed=False
            else:
                accepted=(not invalid_inventory and fee_exec<=maxfee+1e-10)
                failed=(not invalid_inventory and not accepted)
                net=(decision_gross(action,x,fee_exec,ratio,price)-g_success) if accepted else -g_fail
            rows.append(dict(trial=t,policy=label,action=action,submit=submit,
                success=bool(submit and accepted),fee_cap_failure=failed,
                inventory_failure=bool(submit and invalid_inventory),
                ex_post_negative_success=bool(submit and accepted and net<0),
                net_utility_usd=net,quote_fee_char=quote,execution_fee_char=fee_exec))
    df=pd.DataFrame(rows)
    grouped=[]
    for pol,g in df.groupby('policy',sort=False):
        attempts=int(g.submit.sum()); failures=int(g.fee_cap_failure.sum()); succ=int(g.success.sum()); invfails=int(g.inventory_failure.sum())
        grouped.append(dict(policy=pol,total_trials=len(g),submitted=attempts,
            successful=succ,failed_cap=failures,failed_inventory=invfails,
            success_rate_given_submit=succ/attempts,
            ex_post_negative_success_count=int(g.ex_post_negative_success.sum()),
            expected_net_utility_usd_per_arrival=g.net_utility_usd.mean(),
            expected_net_utility_usd_given_submit=g.loc[g.submit,'net_utility_usd'].mean()))
    return pd.DataFrame(grouped),df


def write_fee_split_examples(output_dir:Path):
    projects,q=read_snapshot();Q=float(q.sum());examples=[]
    for j in [0,6]:
        for action in ['deposit','redeem']:
            x=10.
            fee=fee_for(action,float(q[j]),Q,x,'dynamic')
            # Illustrative 70% / 30% recipients; NOT observed on-chain FeeSetup.
            examples.append(dict(project=projects[j],action=action,amount_tco2=x,
                fee_CHAR=fee,recipient_A_char=.7*fee,recipient_B_char=.3*fee,
                depositor_CHAR_minted=(x-fee if action=='deposit' else float('nan')),
                redeemer_CHAR_spent=(x+fee if action=='redeem' else float('nan')),
                assumption='HYPOTHETICAL_70_30_RECIPIENTS_NOT_REAL_FEES_SETUP'))
    pd.DataFrame(examples).to_csv(output_dir/'hypothetical_fee_split_examples.csv',index=False)

def write_self_recapture_examples(output_dir:Path,price=200.,gas=3.):
    projects,q=read_snapshot();Q=float(q.sum());records=[]
    for j,action,ratio in [(0,'deposit',.95),(6,'redeem',1.18)]:
        fee=fee_for(action,float(q[j]),Q,10.,'dynamic')
        for alpha in [0.,.2,.5]:
            val=decision_gross(action,10.,fee,ratio,price,recapture=alpha)-gas
            records.append(dict(project=projects[j],action=action,
                outside_or_buyer_value_relative_to_char=ratio,fee_CHAR=fee,
                assumed_self_recapture_share=alpha,net_participation_gain_USD=val,
                participates=val>=0.,
                assumption='HYPOTHETICAL_SELF_RECIPIENT_PAYOUT_NOT_VERIFIED_CHAR_ROLE'))
    pd.DataFrame(records).to_csv(output_dir/'hypothetical_recapture_participation.csv',index=False)


def simulate_joint(rng_seed=20261119,replications=110,rounds=270,price=200.,g_success=3.,g_fail=2.):
    """Joint design experiment: two users quote same pre-round state; sequential
    execution changes the second call's fee and eligibility. Values/arrivals are
    synthetic, including the assumed trading fee-recipient role (10% chance).
    Budget accounting is CHAR; fee recipient A gets 70%, B gets 30%.
    """
    projects,initial=read_snapshot();n=len(projects);prob=.5*initial/initial.sum()+.5*np.ones(n)/n
    scenarios=[('dynamic','quote_0',0.),('dynamic','quote_0.15',.15),
               ('dynamic','quote_0.75',.75),('dynamic','break_even',None),
               ('flat5','quote_0',0.)]
    rows=[]
    for rep in range(replications):
        rng=np.random.default_rng(rng_seed+rep)
        M=rounds*2
        proj=rng.choice(n,M,p=prob)
        typ=rng.random(M)<.55
        x=rng.uniform(1.,11.,M)
        vr=rng.uniform(.76,1.04,M)
        ur=rng.uniform(1.,1.36,M)
        recipient_A_trader=rng.random(M)<.10
        ordering=rng.random(rounds)<.5
        for rule,cap_name,buffer in scenarios:
            q=initial.copy()
            submitted=successful=failed_cap=failed_inventory=0
            signed_deposits=signed_redeems=0
            volume=fees=utility=0.
            received_A=received_B=0.
            for rd in range(rounds):
                idxs=[2*rd,2*rd+1]
                quoted=[]
                for a in idxs:
                    j=int(proj[a]); qty=float(x[a]); action='deposit' if typ[a] else 'redeem'
                    val=float(vr[a] if typ[a] else ur[a]); alpha=.7 if recipient_A_trader[a] else 0.
                    if action=='redeem' and (q[j]<qty or q.sum()<=qty):
                        quoted.append(None);continue
                    fee=fee_for(action,float(q[j]),float(q.sum()),qty,rule)
                    if decision_gross(action,qty,fee,val,price,alpha)<g_success:
                        quoted.append(None);continue
                    if cap_name=='break_even':
                        cap=(qty*(1-val) if action=='deposit' else qty*(val-1))
                        cap-=(g_success-g_fail)/price
                        if alpha<1:cap/=1-alpha
                    else:cap=fee+buffer
                    quoted.append((j,qty,action,val,alpha,cap))
                order=[1,0] if ordering[rd] else [0,1]
                for ind in order:
                    plan=quoted[ind]
                    if plan is None:continue
                    submitted+=1
                    j,qty,action,val,alpha,cap=plan
                    if action=='redeem' and (q[j]<qty or q.sum()<=qty):
                        failed_inventory+=1;utility-=g_fail;continue
                    fee=fee_for(action,float(q[j]),float(q.sum()),qty,rule)
                    if fee>cap+1e-10:
                        failed_cap+=1;utility-=g_fail;continue
                    successful+=1;volume+=qty;fees+=fee
                    received_A+=.7*fee;received_B+=.3*fee
                    if action=='deposit':q[j]+=qty;signed_deposits+=1
                    else:q[j]-=qty;signed_redeems+=1
                    utility+=decision_gross(action,qty,fee,val,price,alpha)-g_success
            assert abs(received_A+received_B-fees)<1e-6
            rows.append(dict(rep=rep,rule=rule,cap_policy=cap_name,rounds=rounds,
                arrivals=M,submitted=submitted,successful=successful,
                failed_cap=failed_cap,failed_inventory=failed_inventory,
                volume_TCO2=volume,fee_generated_CHAR=fees,
                recipient_A_CHAR=received_A,recipient_B_CHAR=received_B,
                net_payoff_USD_all_traders=utility,HHI=hhi(q),Q_end=q.sum()))
    return pd.DataFrame(rows)

def main():
    a=argparse.ArgumentParser();a.add_argument('--fast',action='store_true');args=a.parse_args()
    _,initial=read_snapshot()
    Q,H=write_boundary(HERE)
    write_fee_split_examples(HERE)
    write_self_recapture_examples(HERE)
    replications,arrivals,trials=(40,400,6000) if args.fast else (160,650,40000)
    df=simulate_policy(replications=replications,arrivals=arrivals)
    df.to_csv(HERE/'policy_simulation_replications.csv',index=False)
    summ=df.groupby('rule').agg(HHI_mean=('HHI','mean'),HHI_std=('HHI','std'),
        accepted_mean=('accepted','mean'),deposit_mean=('deposit_count','mean'),
        redeem_mean=('redeem_count','mean'),volume_mean=('executed_volume','mean'),
        fees_CHAR_mean=('fee_to_recipients_CHAR','mean'),Q_end_mean=('Q_end','mean')).reset_index()
    summ.to_csv(HERE/'policy_simulation_summary.csv',index=False)
    stress_cases=[
        ('high_outside_value',(.91,1.11),(1.,1.36),.5),
        ('low_buyer_value',(.76,1.04),(1.,1.15),.5),
        ('uniform_project_arrivals',(.76,1.04),(1.,1.36),0.),
        ('concentrated_project_arrivals',(.76,1.04),(1.,1.36),1.),
    ]
    sensitivity=[]
    for case,sv,bv,weight in stress_cases:
        dd=simulate_policy(rng_seed=20261216,replications=(25 if args.fast else 60),
                            arrivals=(250 if args.fast else 500),
                            supplier_outside=sv,buyer_value=bv,initial_weight=weight)
        for rule, grp in dd.groupby('rule'):
            sensitivity.append(dict(case=case,rule=rule,HHI_mean=grp.HHI.mean(),
                volume_mean=grp.executed_volume.mean(),
                accepted_mean=grp.accepted.mean(),fees_CHAR_mean=grp.fee_to_recipients_CHAR.mean()))
    pd.DataFrame(sensitivity).to_csv(HERE/'sensitivity_summary.csv',index=False)
    joint=simulate_joint(replications=(25 if args.fast else 110),rounds=(125 if args.fast else 270))
    joint.to_csv(HERE/'joint_mechanism_replications.csv',index=False)
    joint_sum=joint.groupby(['rule','cap_policy'],as_index=False).agg(
       submitted_mean=('submitted','mean'),successful_mean=('successful','mean'),
       failed_cap_mean=('failed_cap','mean'),HHI_mean=('HHI','mean'),
       volume_mean=('volume_TCO2','mean'),fee_generated_CHAR_mean=('fee_generated_CHAR','mean'),
       recipient_A_CHAR_mean=('recipient_A_CHAR','mean'),
       recipient_B_CHAR_mean=('recipient_B_CHAR','mean'),
       trader_payoff_USD_mean=('net_payoff_USD_all_traders','mean'))
    joint_sum.to_csv(HERE/'joint_mechanism_summary.csv',index=False)
    slp, detail=slippage_stress(trials=trials)
    slp.to_csv(HERE/'maxfee_execution_stress_summary.csv',index=False)
    # Avoid producing a very large synthetic data file; summary + code + reproducible seed suffice.
    research_meta={
        'provenance':'PUBLIC_WEBSITE_SNAPSHOT_PLUS_SOURCE_CODE_PLUS_SYNTHETIC_AGENT_ASSUMPTIONS',
        'date':'2026-11-16', 'public_snapshot_Q':Q,'public_snapshot_HHI':H,
        'snapshot_block_number':None, 'observed_char_transaction_count':None,
        'policy_sim_reps':replications,'policy_sim_arrivals_per_rep':arrivals,
        'execution_stress_trials':trials,'joint_synthetic_replications':(25 if args.fast else 110),
        'joint_two_agent_rounds_per_rep':(125 if args.fast else 270),
        'hypothetical_fee_recipient_shares':[0.7,0.3],
        'hypothetical_probability_trader_is_recipient_A':0.10,
        'USD_per_CHAR_ASSUMED':200,
        'success_gas_USD_ASSUMED':3, 'failure_gas_USD_ASSUMED':2,
        'deployed_code_parameter_validation':'NOT_DONE',
        'source_versions':'ToucanProtocol/dynamic-fee-pools FeeCalculator.sol; ToucanProtocol/contracts Pool.sol',
        'fee_fallback_scope':'single-project flat case and negative redemption dust fallback; ignores EVM rounding, cap, seeding, exemptions, pauses, upgrades',
        'sim_model':'exogenous project-arrival, outside values, fixed CHAR price, full eligibility; no causal inference or equilibrium' }
    (HERE/'simulation_metadata.json').write_text(json.dumps(research_meta,indent=2),encoding='utf-8')
    print('PUBLIC SNAPSHOT Q/HHI:',Q,H)
    print('\nPOLICY EXPERIMENT\n',summ.to_string(index=False))
    print('\nEXECUTION STRESS\n',slp.to_string(index=False))
    print('\nJOINT EXPERIMENT\n',joint_sum.to_string(index=False))
    print('\nBOUNDARY CASE\n',pd.read_csv(HERE/'boundary_experiment.csv').to_string(index=False))

if __name__=='__main__':main()
