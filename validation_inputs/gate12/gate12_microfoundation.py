#!/usr/bin/env python3
"""Gate 12: reproducible, entirely SYNTHETIC SCM microfoundation.

Source-based fee formulas are REAL-VALUED approximations to a Toucan published
FeeCalculator (not EVM-equivalent, deployed-state verified or on-chain data).
Economic parameters and producer/intermediary relationships are HYPOTHETICAL.
Outputs must not be described as observed producer revenue or carbon removal.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, localcontext
import csv, json, math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'data'
FIG = ROOT / 'figures'
OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)

D = lambda x: Decimal(str(x))


def deposit_fee(action, q, Q, x, policy='legacy'):
    """Real-number quote in token units; x>0, 0<=q<=Q. No EVM/threshold emulation."""
    q,Q,x=map(D,(q,Q,x))
    if x<=0 or q<0 or Q<0 or q>Q:raise ValueError('Invalid pool state')
    if action not in ('deposit','redeem'): raise ValueError(action)
    if action=='redeem' and (x>q or x>Q):raise ValueError('Not enough inventory')
    with localcontext() as ctx:
        ctx.prec=75
        if q==Q:
            legacy=D('.1')*x
        else:
            a=q/Q
            if action=='deposit':
                b=(q+x)/(Q+x)
                legacy=D('.18')*(q*(D(1)-D('.99')*a).log10() - (q+x)*(D(1)-D('.99')*b).log10())
            else:
                if x>=Q:raise ValueError('Invalid interior redemption')
                b=(q-x)/(Q-x)
                legacy=D('.3')*((q-x)*(b+D('.1')).log10()-q*(a+D('.1')).log10()+x*D('1.1').log10())
        if policy=='legacy':out=legacy
        elif policy=='flat5':out=D('.05')*x
        elif policy=='clipped10':
            # .10x anchor, ensures continuity and monotonicity at q=Q in real arithmetic
            out=min(legacy,D('.10')*x) if action=='deposit' else max(legacy,D('.10')*x)
        elif policy=='extension':
            if action=='deposit':out=D('.36')*x if q==Q and Q>0 else legacy
            else:out=max(D('.001')*x,(D(0) if q==Q and Q>0 else legacy))
        else:raise ValueError(policy)
        return out  # high-precision Decimal; not EVM fixed-point

@dataclass(frozen=True)
class Parameters:
    P: float = 200.0  # hypothetical currency / CHAR
    outside_credit_price: float = 155.0  # hypothetical /CORC
    baseline_procurement_price: float = 140.0  # hypothetical /CORC
    beta: float = 0.5  # contractually passed fraction of incremental monetization premium
    eta: float = 0.8  # verified net CORCs per physical biochar unit (assumed)
    cost_linear: float = 70.0  # per physical biochar unit (assumed)
    cost_quadratic: float = 1.1  # positive physical production cost curvature
    gas: float = 3.0  # fixed successful execution cost, hypothetical currency
    failed_gas: float = 2.0  # failed submitted transaction cost, hypothetical
    execution_probability: float = 1.0  # assumed success conditional on submission (NOT measured)
    order_size: float = 10.0  # CORCs per quote
    liquidity: float | None = None  # available pre-production currency, None => not binding
    buyer_u_low: float = 175.0  # illustrative buyer values per CORC
    buyer_u_high: float = 270.0

def production_cap(p: Parameters):
    if p.liquidity is None:return math.inf
    if p.liquidity<0:raise ValueError('Negative working capital')
    c,k=p.cost_linear,p.cost_quadratic
    return (math.sqrt(c*c+2*k*p.liquidity)-c)/k

def market_outcome(q, Q, policy, p: Parameters):
    """One marginal seller and buyer facing exogenous, anticipated state.
    Ex-ante producer contract is b=b0+beta * max(monetization - outside,0).
    This is NOT a global equilibrium or a measured CHAR commercial contract.
    """
    fD = float(deposit_fee('deposit',q,Q,p.order_size,policy))
    fR = float(deposit_fee('redeem',q,Q,p.order_size,policy)) if q>=p.order_size else float('nan')
    d=fD/p.order_size
    expected_pool_net_price = p.P*(1-d)-p.gas/p.order_size
    if not 0<=p.execution_probability<=1:raise ValueError('Execution probability must be in [0,1]')
    expected_net_advantage=(p.execution_probability*(expected_pool_net_price-p.outside_credit_price)
                          -(1-p.execution_probability)*p.failed_gas/p.order_size)
    premium=max(0.0,expected_net_advantage)
    upstream_unit_price=p.baseline_procurement_price+p.beta*premium
    unconstrained=max(0.0,(p.eta*upstream_unit_price-p.cost_linear)/p.cost_quadratic)
    y=min(unconstrained,production_cap(p))
    net_certified=p.eta*y  # hypothetical certified net removal if physical process is eligible
    broker_price=max(expected_pool_net_price,p.outside_credit_price)
    broker_margin_per_corc=broker_price-upstream_unit_price
    if math.isfinite(fR):
        buyer_threshold=p.P*(1+fR/p.order_size)+p.gas/p.order_size
        buyer_share=max(0.0,min(1.0,(p.buyer_u_high-buyer_threshold)/(p.buyer_u_high-p.buyer_u_low)))
    else:buyer_threshold=buyer_share=float('nan')
    return dict(
        deposit_fee_CHAR=fD,deposit_fee_rate=d,redemption_fee_CHAR=fR,
        net_pool_realization_currency_per_C=expected_pool_net_price,
        pooling_premium_currency_per_C=premium,execution_probability=p.execution_probability,
        expected_net_advantage_currency_per_C=expected_net_advantage,producer_unit_procurement_currency=upstream_unit_price,
        intermediary_margin_currency_per_C=broker_margin_per_corc,
        physical_biochar_output_units=y,illustrative_verified_CORCs=net_certified,
        unconstrained_output_units=unconstrained,working_capital_cap_units=production_cap(p),
        buyer_min_value_currency_per_C=buyer_threshold,
        model_redemption_propensity=buyer_share)

def write_csv(filename,rows):
    with (OUT/filename).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def run_tests():
    assert abs(float(deposit_fee('deposit',100,100,10))-1)<1e-12
    assert abs(float(deposit_fee('redeem',100,100,10))-1)<1e-12
    assert abs(float(deposit_fee('deposit',100,100.000001,10))-3.6)<1e-6
    assert abs(float(deposit_fee('redeem',100,100.000001,10)))<1e-6
    assert abs(float(deposit_fee('deposit',100,100,10,'extension'))-3.6)<1e-10
    assert abs(float(deposit_fee('deposit',100,100.000001,10,'clipped10'))-1)<1e-10
    for policy in ['legacy','flat5','clipped10','extension']:
        for q,Q in [(100,100),(100,100.01),(367.093,815.959)]:
            for action in ['deposit','redeem']:
                x=float(deposit_fee(action,q,Q,10,policy));assert 0<=x<10, (policy,action,q,Q,x)
    for beta in [0, .25,.5,1]:
        from dataclasses import replace
        p=replace(Parameters(),beta=beta)
        out=market_outcome(100,100,p=p,policy='legacy')
        outnear=market_outcome(100,100.00001,p=p,policy='legacy')
        if beta==0:assert abs(out['physical_biochar_output_units']-outnear['physical_biochar_output_units'])<1e-9
        else:assert out['physical_biochar_output_units']>outnear['physical_biochar_output_units']
    from dataclasses import replace
    p=replace(Parameters(),beta=.5,liquidity=1000)
    assert abs(market_outcome(100,100,'legacy',p)['physical_biochar_output_units']-market_outcome(100,100.001,'legacy',p)['physical_biochar_output_units'])<1e-10
    # Interior derivative theorem: take a synthetic positive pool premium and slack financing.
    p=replace(Parameters(),outside_credit_price=110,liquidity=None,beta=.5)
    d=.1;h=1e-6
    def y_d(d):
        r=p.P*(1-d)-p.gas/p.order_size
        b=p.baseline_procurement_price+p.beta*max(0,r-p.outside_credit_price)
        return max(0.,(p.eta*b-p.cost_linear)/p.cost_quadratic)
    finite=(y_d(d+h)-y_d(d-h))/(2*h)
    analytic=-p.eta*p.beta*p.P/p.cost_quadratic
    assert abs(finite-analytic)<1e-7, (finite,analytic)
    return {'tests_passed':True,'derivative_numeric':finite,'derivative_formula':analytic,'warning':'Pure real-number and structural-economic tests; NOT EVM verification'}

def main():
    from dataclasses import replace
    tests=run_tests()
    scenarios={
      'single_project_100_0':(100.0,100.0),
      'near_monopoly_100_0.01':(100.0,100.01),
      'near_monopoly_100_1':(100.0,101.0),
      'seven_project_snapshot_project_A':(367.093,815.959)
    }
    policies=['legacy','clipped10','extension','flat5']
    rows=[]
    for name,(q,Q) in scenarios.items():
        for pol in policies:
            p=Parameters()
            rows.append(dict(scenario=name,policy=pol,beta=p.beta,working_capital='unconstrained',q=q,Q=Q,**market_outcome(q,Q,pol,p)))
    write_csv('scenario_results_SYNTHETIC.csv',rows)
    sens=[]
    for name,(q,Q) in scenarios.items():
      for beta in [0,.25,.5,.75,1]:
       for L in [1000,2500,6000,None]:
        for pol in policies:
          p=replace(Parameters(),beta=beta,liquidity=L)
          sens.append(dict(scenario=name,policy=pol,beta=beta,capital_L='unconstrained' if L is None else L,q=q,Q=Q,**market_outcome(q,Q,pol,p)))
    write_csv('beta_liquidity_sensitivity_SYNTHETIC.csv',sens)
    execution_sensitivity=[]
    for name,(q,Q) in scenarios.items():
      for prob in [0.25,0.5,0.75,1.0]:
       for beta in [0,0.5,1.0]:
        for pol in policies:
         p=replace(Parameters(),execution_probability=prob,beta=beta)
         execution_sensitivity.append(dict(scenario=name,policy=pol,beta=beta,success_prob=prob,q=q,Q=Q,**market_outcome(q,Q,pol,p)))
    write_csv('execution_sensitivity_SYNTHETIC.csv',execution_sensitivity)
    epss=[0,Decimal('0.000000001'),Decimal('0.000001'),Decimal('0.001'),Decimal('0.01'),Decimal('.1'),Decimal('1'),Decimal('10')]
    b=[]
    for eps in epss:
        Q=D('100')+eps
        for pol in policies:
            p=Parameters()
            b.append(dict(other_project_TCO2=str(eps),policy=pol,
                 deposit_fee_CHAR=str(deposit_fee('deposit',100,Q,10,pol)),
                 redeem_fee_CHAR=str(deposit_fee('redeem',100,Q,10,pol)),
                 hypothetical_output_units=market_outcome(100,Q,pol,p)['physical_biochar_output_units']))
    write_csv('boundary_and_upstream_SYNTHETIC.csv',b)
    # Visualization: no explicit color parameters.
    fig,ax=plt.subplots(figsize=(8,4.7))
    for pol in policies:
        xs=[float(eps) for eps in epss[1:]]
        ys=[market_outcome(100,D('100')+eps,pol,Parameters())['physical_biochar_output_units'] for eps in epss[1:]]
        ax.plot(xs,ys,marker='o',label=pol)
    ax.set_xscale('log');ax.set_xlabel('Other-project balance (TCO2; synthetic)')
    ax.set_ylabel('Producer output (model units)')
    ax.set_title('Conditional upstream transmission of boundary fee rules')
    ax.legend();fig.tight_layout();fig.savefig(FIG/'output_boundary_pass_through.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.7))
    for pol in policies:
        xs=[0,.25,.5,.75,1]
        ys=[market_outcome(100,100,pol,replace(Parameters(),beta=beta))['physical_biochar_output_units'] for beta in xs]
        ax.plot(xs,ys,marker='o',label=pol)
    ax.set_xlabel('Contractual pass-through beta (synthetic)')
    ax.set_ylabel('Producer output (model units)')
    ax.set_title('Fee-rule effects require upstream pass-through')
    ax.legend();fig.tight_layout();fig.savefig(FIG/'producer_output_beta.png',dpi=180);plt.close(fig)
    report={'script':'gate12_microfoundation.py','status':'SYNTHETIC_ONLY',
            'assumptions':vars(Parameters()), 'source_formula':'ToucanProtocol/dynamic-fee-pools src/FeeCalculator.sol real-number representation',
            'propositions_tests':tests,'scenario_count':len(rows),'sensitivity_count':len(sens),'boundary_cases':len(b),'execution_sensitivity_count':len(execution_sensitivity),
            'onchain_data_rows':0,'foundry_tests_executed':False,'producer_wallets_attributed':0,
            'important_note':'No real prices, producer contracts, royalties, issuance, or additional physical CDR were measured'}
    (OUT/'RUN_METADATA.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Passed checks; synthetic scenarios=',len(rows),'sensitivity=',len(sens))
    for r in rows:
        if r['scenario'] in ('single_project_100_0','near_monopoly_100_0.01') and r['policy'] in ('legacy','clipped10','extension'):
            print(r['scenario'],r['policy'],'fee%',round(100*r['deposit_fee_rate'],5),'y',round(r['physical_biochar_output_units'],5))

if __name__=='__main__': main()
