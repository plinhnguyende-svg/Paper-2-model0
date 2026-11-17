"""Gate 10, independently rerunnable numerical mechanism experiment.

NO EVM/Foundry execution is claimed by this script. Source policy is a real-number
representation of Toucan's 2024 FeeCalculator source parameters, excluding EVM
rounding, reverts, exemptions, seeding/cap, and deployed version changes.
The other policies are RESEARCH PROPOSALS, not deployed CHAR code. All agents,
arrivals, prices, recipient identities and valuations are synthetic. SHA source
reference: ToucanProtocol/dynamic-fee-pools 7aef954dae1bd0c7add4ed66d216251110521b16.
"""
from __future__ import annotations
import argparse, csv, math
from decimal import Decimal, localcontext
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; FIG=ROOT/'figures'
DATA.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)


def source_fee(action: str, q: float, Q: float, x: float) -> float:
    """Real-number source-formula replica; does not emulate EVM arithmetic."""
    if not (Q >= 0 and 0<=q<=Q+1e-10 and x>0): raise ValueError('invalid inventory')
    if action == 'redeem' and (x>q or x>=Q): raise ValueError('invalid redemption')
    if action not in ('deposit','redeem'): raise ValueError('unknown action')
    if q==Q: return .1*x
    if action=='deposit':
        a=q/Q;b=(q+x)/(Q+x)
        return .18*(q*math.log10(1-.99*a)-(q+x)*math.log10(1-.99*b))
    # Cancellation near q/Q = 1 can cause a FALSE negative fee in float,
    # activating the dust fallback spuriously. Compute near-boundary real
    # arithmetic with 65-digit Decimal as an independent numerical safeguard.
    if (Q-q)/Q < 1e-4:
        with localcontext() as ctx:
            ctx.prec=65
            dq=Decimal(str(q)); dQ=Decimal(str(Q)); dx=Decimal(str(x))
            ln10=Decimal(10).ln(); dshift=Decimal('0.1')
            a=dq/dQ;b=(dq-dx)/(dQ-dx)
            val=Decimal('0.30')*((dq-dx)*(b+dshift).ln()/ln10
                    -dq*(a+dshift).ln()/ln10+dx*Decimal('1.1').ln()/ln10)
            return float(Decimal('0.30')*dx) if val<0 else max(0.0,float(val))
    a=q/Q;b=(q-x)/(Q-x)
    val=.30*((q-x)*math.log10(b+.1)-q*math.log10(a+.1)+x*math.log10(1.1))
    return .30*x if val<0 else max(0,val)


def alternative_fee(action, q, Q, x, policy):
    """Three proposed designs: anchored smooth, continuous extension, flat5."""
    base=source_fee(action,q,Q,x)
    if policy=='source': return base
    if policy=='flat5': return .05*x
    if policy.startswith('smooth_'):
        tau=float(policy.split('_')[1]);
        if Q==0:return .10*x
        # other project's inventory m=Q-q; at exactly mono m=0, anchor is 10%.
        m=max(0,Q-q);w=m/(m+tau*Q)
        return (1-w)*(.10*x)+w*base
    if policy=='ext_floor':
        # Continuation of interior real-number rule at single-project boundary:
        # 36% deposit, 0.1% redemption floor; not deployed EVM code.
        if Q==0:return .10*x
        if action=='deposit': return .36*x if q==Q else base
        return max(.001*x,0 if q==Q else base)
    raise ValueError(policy)


def hhi(q):
    Q=sum(q);return sum((v/Q)**2 for v in q) if Q>0 else math.nan


def boundary_grid():
    rows=[]
    for eps in [0., 1., .1, .01, .001, .00001, .0000001]:
        for action in ['deposit','redeem']:
            record=dict(other_project_quantity=eps,dominant_quantity=100.,action=action,amount=10.)
            for policy in ['source','smooth_0.01','smooth_0.03','ext_floor','flat5']:
                record[policy]=alternative_fee(action,100.,100.+eps,10.,policy)
            rows.append(record)
    pd.DataFrame(rows).to_csv(DATA/'boundary_fee_grid.csv',index=False)
    return pd.DataFrame(rows)


def simulate(replications=100, rounds=180, seed=2026111610):
    snapshot=pd.read_csv(DATA/'public_indexed_char_snapshot.csv')
    base=snapshot['inventory_tco2'].values.astype(float)
    scenarios={'real_site_snapshot':base,
               'near_mono_stress_TEST_ONLY':np.array([100.,.1]),
               'exact_mono_stress_TEST_ONLY':np.array([100.,0.])}
    policies=['source','smooth_0.01','smooth_0.03','ext_floor','flat5']
    cap_rules=['exact_quote','quote_plus_0.15','economic_cap']
    results=[]
    for setting,initial in scenarios.items():
        n=len(initial)
        p=.45*initial/initial.sum()+.55*np.ones(n)/n
        for rep in range(replications):
            rng=np.random.default_rng(seed+rep+(0 if setting=='real_site_snapshot' else (100000 if setting.startswith('near') else 200000)))
            M=2*rounds
            projs=rng.choice(n,M,p=p)
            deposit=rng.random(M)<.55
            amounts=rng.uniform(1.0,10.,M)
            outside=rng.uniform(.75,1.05,M)
            buyer=rng.uniform(.98,1.35,M)
            recipient_owner=rng.random(M)<.08 # purely synthetic agent attribute
            order=rng.random(rounds)<.5
            for policy in policies:
                for cap_type in cap_rules:
                    q=initial.copy();n_submitted=n_executed=n_capfail=n_invfail=0
                    gross_value=0.;received_A=0.;received_B=0.;volume=0.;fees=0.;n_deposits=n_redeems=0
                    for rd in range(rounds):
                        selected=[2*rd,2*rd+1]
                        plans={}
                        # Both participants observe same beginning-of-round inventory.
                        Q=float(q.sum())
                        for i in selected:
                            j=int(projs[i]);x=float(amounts[i]);act='deposit' if deposit[i] else 'redeem'
                            if act=='redeem' and (q[j]<x or Q<=x):continue
                            f=alternative_fee(act,float(q[j]),Q,x,policy)
                            val=float(outside[i] if act=='deposit' else buyer[i])
                            # Receive a synthetic 70% fee share for 8% agents, without assuming real producer identity.
                            alpha=.7 if recipient_owner[i] else 0.
                            before=(x*(1-val) if act=='deposit' else x*(val-1))*200-(1-alpha)*f*200
                            if before < 3.0:continue
                            if cap_type=='economic_cap':
                                # A fee recipient's own share is treated as immediately recapturable in this toy model.
                                cap=((x*(1-val) if act=='deposit' else x*(val-1))-(3.-2.)/200)/(1-alpha)
                            elif cap_type=='quote_plus_0.15':cap=f+.15
                            else:cap=f
                            if cap<0:continue
                            plans[i]=(j,x,act,val,alpha,cap)
                        execution=[selected[1],selected[0]] if order[rd] else selected
                        for i in execution:
                            if i not in plans:continue
                            n_submitted+=1
                            j,x,act,val,alpha,cap=plans[i]
                            Q=float(q.sum())
                            if act=='redeem' and (q[j]<x or Q<=x):
                                n_invfail+=1;gross_value-=2.;continue
                            f=alternative_fee(act,float(q[j]),Q,x,policy)
                            if f>cap+1e-9:
                                n_capfail+=1;gross_value-=2.;continue
                            n_executed+=1;volume+=x;fees+=f
                            received_A+=.7*f;received_B+=.3*f
                            q[j]+=(x if act=='deposit' else -x)
                            n_deposits+=(act=='deposit');n_redeems+=(act=='redeem')
                            gross_value+=((x*(1-val) if act=='deposit' else x*(val-1))-(1-alpha)*f)*200-3.
                    assert n_submitted==n_executed+n_capfail+n_invfail
                    assert abs(received_A+received_B-fees)<1e-7
                    results.append(dict(scenario=setting,rep=rep,policy=policy,cap_rule=cap_type,
                             offered=2*rounds,submitted=n_submitted,executed=n_executed,
                             fail_cap=n_capfail,fail_inventory=n_invfail,deposits=n_deposits,
                             redemptions=n_redeems,final_HHI=hhi(q),initial_HHI=hhi(initial),
                             total_volume=volume,total_fees_CHAR=fees,recipient_A_CHAR=received_A,
                             recipient_B_CHAR=received_B,participant_surplus_model_USD=gross_value,
                             final_Q=float(q.sum())))
    runs=pd.DataFrame(results)
    runs.to_csv(DATA/'policy_replications_SYNTHETIC.csv',index=False)
    summary=runs.groupby(['scenario','policy','cap_rule'],as_index=False).agg(
       initial_HHI=('initial_HHI','mean'),final_HHI=('final_HHI','mean'),
       hhi_sd=('final_HHI','std'),executed=('executed','mean'),submitted=('submitted','mean'),
       fail_cap=('fail_cap','mean'),fees_CHAR=('total_fees_CHAR','mean'),
       volume=('total_volume','mean'),participant_surplus_USD=('participant_surplus_model_USD','mean'),
       recipient_A_CHAR=('recipient_A_CHAR','mean'),recipient_B_CHAR=('recipient_B_CHAR','mean'))
    summary['completion_given_submit']=summary['executed']/summary['submitted']
    summary['delta_HHI']=summary['final_HHI']-summary['initial_HHI']
    summary.to_csv(DATA/'policy_summary_SYNTHETIC.csv',index=False)
    return summary


def tests():
    # Source formula discontinuity at mono boundary.
    for action in ['deposit','redeem']:
        src=source_fee(action,100,100,10)
        assert math.isclose(src,1.,abs_tol=1e-12)
        near=source_fee(action,100,100+1e-6,10)
        assert abs(near-(3.6 if action=='deposit' else 0.))<1e-6
        for p in ['smooth_0.01','smooth_0.03']:
            v=alternative_fee(action,100,100+1e-6,10,p)
            assert abs(v-1.)<1e-4
        ext=alternative_fee(action,100,100+1e-6,10,'ext_floor')
        mono=alternative_fee(action,100,100,10,'ext_floor')
        assert abs(ext-mono)<1e-5
    assert math.isclose(hhi([100.,0.]),1.)
    for p in ['source','smooth_0.01','smooth_0.03','ext_floor','flat5']:
        for act in ('deposit','redeem'):
            for q,Q,x in [(100.,101.,10.),(0.,100.,10.)] if act=='deposit' else [(100.,101.,10.),(50.,100.,10.)]:
                fee=alternative_fee(act,q,Q,x,p)
                assert fee>=-1e-8, (p,act,q,Q,x,fee)
                assert fee<=x, (p,act,q,Q,x,fee)
    return 'analytic/numerical checks PASS (not EVM tests)'


def figures(summary,boundary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for action in ('deposit','redeem'):
        d=boundary[boundary.action==action].sort_values('other_project_quantity')
        fig,ax=plt.subplots(figsize=(8,4.7))
        for p in ['source','smooth_0.01','smooth_0.03','ext_floor','flat5']:
            ax.plot(d['other_project_quantity'],d[p],marker='o',label=p)
        ax.set_xscale('symlog',linthresh=1e-7)
        ax.set_xlabel('Other-project inventory (TCO2), 100 TCO2 in project A')
        ax.set_ylabel('Fee in CHAR for 10 TCO2')
        ax.set_title(f'Boundary experiment: {action} (mathematical simulation)')
        ax.legend(loc='best',fontsize=8);ax.grid(alpha=.2)
        fig.tight_layout();fig.savefig(FIG/f'boundary_{action}.png',dpi=150);plt.close(fig)
    d=summary[(summary.scenario=='near_mono_stress_TEST_ONLY')&(summary.cap_rule=='quote_plus_0.15')]
    fig,ax=plt.subplots(figsize=(8.6,4.7))
    ax.bar(d.policy,d.final_HHI)
    ax.set_ylabel('Mean final HHI')
    ax.set_title('Near-monopoly stress: policy trade-off (synthetic)')
    ax.tick_params(axis='x',rotation=25);fig.tight_layout();fig.savefig(FIG/'near_mono_composition.png',dpi=150);plt.close(fig)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');args=ap.parse_args()
    print(tests())
    b=boundary_grid()
    s=simulate(replications=(12 if args.quick else 100),rounds=(50 if args.quick else 180))
    figures(s,b)
    print(s[(s.scenario=='near_mono_stress_TEST_ONLY')&(s.cap_rule=='quote_plus_0.15')][['policy','final_HHI','executed','fees_CHAR','completion_given_submit']].to_string(index=False))
    print('Results in',DATA,'; figures in',FIG)
if __name__=='__main__':main()
