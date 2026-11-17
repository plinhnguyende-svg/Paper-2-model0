#!/usr/bin/env python3
"""Endogenous all-output single-batch model; real arithmetic, not deployed EVM."""
from dataclasses import dataclass, asdict, replace
from decimal import Decimal as D, localcontext
from pathlib import Path
import argparse
import csv
import json


@dataclass(frozen=True)
class Parameters:
    q: D = D('70')
    Q: D = D('100')
    eta: D = D('1')
    P: D = D('1')
    v: D = D('.75')
    b0: D = D('.5')
    beta: D = D('.5')
    c: D = D('.1')
    k: D = D('.01')
    gas: D = D('.1')
    liquidity: D | None = None
    scale: D = D('.18')
    ratio: D = D('.99')
    single_rate: D = D('.10')


def validate(p):
    if not (p.Q > 0 and 0 <= p.q <= p.Q and p.eta > 0 and p.P > 0
            and 0 <= p.b0 <= p.v and 0 <= p.beta <= 1 and p.c >= 0 and p.k > 0
            and p.gas > 0 and p.scale > 0 and p.ratio > 0 and 0 < p.single_rate <= 1
            and (p.liquidity is None or p.liquidity >= 0)):
        raise ValueError('parameters outside master specification')


def liquidity_bound(p):
    if p.liquidity is None:
        return D('Infinity')
    if p.liquidity == 0:
        return D(0)
    # Rationalized form avoids cancellation for small positive liquidity.
    return 2*p.liquidity/((p.c*p.c+2*p.k*p.liquidity).sqrt()+p.c)


def domain_bound(p):
    if p.q == p.Q or p.ratio <= 1:
        return D('Infinity')
    return (p.Q-p.ratio*p.q)/(p.ratio-1)/p.eta


def deposit(x,p):
    """Return F,F',F'' in the smooth real-formula branch. x=0 is analytical extension."""
    if x < 0:
        raise ValueError('negative quantity')
    if p.q == p.Q:
        return p.single_rate*x,p.single_rate,D(0)
    h=p.Q-p.q;z=p.q+x
    A=(1-p.ratio)*z+h;B=z+h
    if A <= 0:
        raise ValueError('log domain')
    initial=1-p.ratio*p.q/p.Q
    if initial <= 0:
        raise ValueError('initial log domain')
    ln10=D(10).ln()
    F=p.scale*(p.q*initial.log10()-z*(A/B).log10())
    marginal=p.scale/ln10*(-(A/B).ln()+p.ratio*h*z/(A*B))
    curvature=p.scale*p.ratio*h*h*(A+B)/(ln10*A*A*B*B)
    if x == 0:
        F=D(0)
    return F,marginal,curvature


def outside_profit(y,p):
    return (p.eta*p.b0-p.c)*y-p.k*y*y/2


def premium_total(y,p):
    F,_,_=deposit(p.eta*y,p)
    return (p.P-p.v)*p.eta*y-p.P*F-p.gas


def pool_profit(y,p):
    return outside_profit(y,p)+p.beta*premium_total(y,p)


def pool_slope(y,p):
    _,marginal,_=deposit(p.eta*y,p)
    return p.eta*p.b0-p.c-p.k*y+p.beta*p.eta*(p.P-p.v-p.P*marginal)


def solve(p):
    validate(p)
    with localcontext() as ctx:
        ctx.prec=75
        cap=liquidity_bound(p)
        y_out=min(cap,max(D(0),(p.eta*p.b0-p.c)/p.k))
        outside=dict(channel='outside',y=y_out,profit=outside_profit(y_out,p),premium=D(0))
        result=dict(outside=outside,pool=None,chosen=outside,numerical_tie=False,
                    root_bracket=None,scope='globally reduced two-branch REAL model; not EVM or market equilibrium')
        if p.beta == 0 or cap == 0 or domain_bound(p) <= 0:
            if p.beta == 0 and y_out > 0 and domain_bound(p) > y_out:
                if premium_total(y_out,p) > 0:
                    result['chosen']=dict(outside,channel='pool',premium=premium_total(y_out,p),fee=deposit(p.eta*y_out,p)[0])
            return result
        if pool_slope(D(0),p) <= 0:
            # Continuous pool branch is decreasing from -beta*gas at zero.
            return result
        bound=domain_bound(p)
        # Locate a nonpositive slope or an attainable liquidity endpoint.
        hi=min(D(1),cap)
        if hi >= bound:
            hi=bound/2
        while pool_slope(hi,p) > 0:
            if hi == cap:
                break
            new=min(hi*2,cap)
            if new >= bound:
                new=(hi+bound)/2
            if new <= hi or new >= bound:
                raise ArithmeticError('root bracket exhausted Decimal resolution')
            hi=new
        if hi == cap and pool_slope(hi,p) >= 0:
            y_pool=cap;bracket=(cap,cap)
        else:
            lo=D(0)
            for _ in range(200):
                mid=(lo+hi)/2
                if pool_slope(mid,p)>0:
                    lo=mid
                else:
                    hi=mid
            y_pool=(lo+hi)/2;bracket=(lo,hi)
        F,_,_=deposit(p.eta*y_pool,p)
        pool=dict(channel='pool',y=y_pool,profit=pool_profit(y_pool,p),premium=premium_total(y_pool,p),fee=F)
        result['pool']=pool;result['root_bracket']=bracket
        gap=pool['profit']-outside['profit']
        # Numeric near-tie only, not a symbolic equality or uniqueness certificate.
        tolerance=D('1e-45')
        result['numerical_tie']=abs(gap)<=tolerance
        if gap>tolerance:
            if not (pool['premium']>0 and 0<F<p.eta*y_pool):
                raise ArithmeticError('profitable pool optimum must be executable at calculator fee guards')
            result['chosen']=pool
        result['profit_gap']=gap
        return result


def scenarios():
    base=Parameters()
    rows=[]
    for label,scale,ratio in [('S0',D('.18'),D('.99')),
                              ('H0_parameter_counterfactual',D('.15'),D('1.25'))]:
        for q in map(D,['0','50','70','79','80','99','100']):
            for v in map(D,['.55','.75','.90']):
                for beta in map(D,['0','.25','.5','1']):
                    for L in [None,D('5'),D('50')]:
                        p=replace(base,q=q,v=v,beta=beta,liquidity=L,scale=scale,ratio=ratio)
                        r=solve(p);a=r['chosen'];o=r['outside']
                        # Frozen premium evaluated at outside-optimal lot is a diagnostic,
                        # not the old model's unique calibration or an observed contract.
                        frozen=None
                        if o['y']>0:
                            try:
                                d=max(D(0),premium_total(o['y'],p)/(p.eta*o['y']))
                                frozen=min(liquidity_bound(p),max(D(0),(p.eta*(p.b0+p.beta*d)-p.c)/p.k))
                            except ValueError:
                                pass
                        rows.append(dict(benchmark=label,q=str(q),v=str(v),beta=str(beta),
                                         L='unbounded' if L is None else str(L),channel=a['channel'],
                                         y=str(a['y']),outside_y=str(o['y']),
                                         output_change=str(a['y']-o['y']),profit=str(a['profit']),
                                         frozen_at_outside_lot_y=None if frozen is None else str(frozen),
                                         pool_profit_gap=None if r.get('profit_gap') is None else str(r['profit_gap']),
                                         numerical_tie=r['numerical_tie']))
    return rows


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='results/gate19')
    args=parser.parse_args()
    root=Path(args.out);root.mkdir(parents=True,exist_ok=True)
    rows=scenarios()
    with (root/'endogenous_quantity_SYNTHETIC.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    lower=[r for r in rows if D(r['output_change'])<D('-1e-30')]
    summary=dict(scenarios=len(rows),pool_selected=sum(r['channel']=='pool' for r in rows),
                 lower_output_despite_pool_option=len(lower),
                 example=lower[0] if lower else None,
                 formula_scope='REAL source formula; H0 is parameterized counterfactual, not deployed oracle',
                 economic_scope='fixed contract beta and exogenous price; no direct producer royalties',
                 global_solution='analytic reduction to two strictly concave branches; 200-step Decimal root bisection',
                 empirical_status='NOT_IDENTIFIED')
    (root/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
    p=replace(Parameters(),ratio=D('1.25'),scale=D('.15'),v=D('.55'),beta=D('.25'),c=D('.15'))
    r=solve(p)
    with localcontext() as ctx:
        ctx.prec=75
        F,marginal,_=deposit(p.eta*r['chosen']['y'],p)
        detail=dict(parameters=asdict(p),outside=r['outside'],selected=r['chosen'],
                    marginal_fee=marginal,average_fee=F/(p.eta*r['chosen']['y']),
                    S_without_gas_at_outside=premium_total(r['outside']['y'],p)+p.gas,
                    marginal_S_at_outside=p.eta*(p.P-p.v-p.P*deposit(p.eta*r['outside']['y'],p)[1]),
                    critical_gas=p.gas+r['profit_gap']/p.beta,
                    provenance='SYNTHETIC sufficient-condition example; H0 parameter counterfactual, not deployed observation')
    (root/'sufficient_condition_example_SYNTHETIC.json').write_text(json.dumps(detail,indent=2,default=str)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
