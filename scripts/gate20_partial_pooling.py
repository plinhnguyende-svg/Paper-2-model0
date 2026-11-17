#!/usr/bin/env python3
"""Gate 20: continuous partial pooling; real formulas, not EVM execution."""
from dataclasses import replace
from decimal import Decimal as D, localcontext
from pathlib import Path
import argparse
import csv
import json
from gate19_endogenous import (Parameters, validate, deposit, liquidity_bound,
                              domain_bound, outside_profit, solve as solve_all_output)


def gross_gain(z,p):
    if z == 0:
        return D(0)
    return (p.P-p.v)*z-p.P*deposit(z,p)[0]


def marginal_gain(z,p):
    return p.P-p.v-p.P*deposit(z,p)[1]


def optimal_lot_limit(p):
    """Unconstrained maximizer of gross pooling gain, before gas and supply cap.
    Infinity means gain increases at every finite amount, not an infinite action.
    """
    if p.q != p.Q and domain_bound(p) <= 0:
        return D(0)
    if marginal_gain(D(0),p) <= 0:
        return D(0)
    if p.q == p.Q:
        return D('Infinity')
    if p.ratio < 1:
        limiting_fee=-p.scale*(1-p.ratio).log10()
        if p.P-p.v >= p.P*limiting_fee:
            return D('Infinity')
    bound=domain_bound(p)*p.eta
    hi=D(1)
    if hi >= bound:
        hi=bound/2
    while marginal_gain(hi,p)>0:
        new=hi*2
        if new >= bound:
            new=(hi+bound)/2
        if new <= hi or new >= bound:
            raise ArithmeticError('lot bracket exhausted Decimal resolution')
        hi=new
    lo=D(0)
    for _ in range(200):
        mid=(lo+hi)/2
        if marginal_gain(mid,p)>0:
            lo=mid
        else:
            hi=mid
    return (lo+hi)/2


def solve_partial(p):
    validate(p)
    with localcontext() as ctx:
        ctx.prec=75
        cap=liquidity_bound(p)
        y0=min(cap,max(D(0),(p.eta*p.b0-p.c)/p.k))
        outside=dict(channel='outside',y=y0,z=D(0),profit=outside_profit(y0,p),premium=D(0))
        limit=optimal_lot_limit(p)
        result=dict(outside=outside,chosen=outside,active_pool=None,lot_limit=limit,
                    numerical_tie=False,scope='continuous partial-venue allocation under real-formula assumptions')
        if limit == 0 or cap == 0:
            return result
        def candidate(y):
            z=min(p.eta*y,limit)
            S=gross_gain(z,p)-p.gas
            return dict(channel='full_pool' if z==p.eta*y else 'partial_pool',
                        y=y,z=z,profit=outside_profit(y,p)+p.beta*S,premium=S,
                        outside_credits=p.eta*y-z,fee=deposit(z,p)[0] if z>0 else D(0))
        if p.beta == 0:
            at_y0=candidate(y0)
            if y0>0 and at_y0['premium']>0:
                result['chosen']=at_y0
            return result
        if p.eta*y0>=limit:
            # Outside production already supplies the surplus-maximizing pool lot.
            # Both the base profit and pooling surplus attain maxima at y0.
            active=candidate(y0);gap=active['profit']-outside['profit']
            result.update(active_pool=active,profit_gap=gap,numerical_tie=abs(gap)<=D('1e-45'))
            if gap>D('1e-45'):
                result['chosen']=active
            return result
        def slope(y):
            if p.eta*y>=limit:
                extra=D(0)
            else:
                extra=p.eta*marginal_gain(p.eta*y,p)
            return p.eta*p.b0-p.c-p.k*y+p.beta*extra
        if slope(D(0)) <= 0:
            return result
        hi=min(D(1),cap)
        while slope(hi)>0:
            if hi == cap:
                break
            new=min(hi*2,cap)
            if new <= hi:
                raise ArithmeticError('production bracket exhausted Decimal resolution')
            hi=new
        if hi == cap and slope(hi)>=0:
            y=cap
        else:
            lo=D(0)
            for _ in range(200):
                mid=(lo+hi)/2
                if slope(mid)>0:
                    lo=mid
                else:
                    hi=mid
            y=(lo+hi)/2
        active=candidate(y);gap=active['profit']-outside['profit']
        result.update(active_pool=active,profit_gap=gap,numerical_tie=abs(gap)<=D('1e-45'))
        if gap>D('1e-45'):
            if active['premium']<=0 or not 0<active['fee']<active['z']:
                raise ArithmeticError('profitable active solution violates quote guards')
            result['chosen']=active
        return result


def batch_fees(p,batches):
    """Sequential same-project self-batches; parameters and all other flows fixed."""
    if any(z<=0 for z in batches):
        raise ValueError('batches must be positive')
    total=D(0);current=p
    for z in batches:
        total+=deposit(z,current)[0]
        current=replace(current,q=current.q+z,Q=current.Q+z)
    return total


def sweep():
    rows=[]
    for label,a,r in [('S0',D('.18'),D('.99')),('H0_parameter_counterfactual',D('.15'),D('1.25'))]:
        for q in map(D,['0','50','70','79','80','99','100']):
            for v in map(D,['.55','.75','.90']):
                for beta in map(D,['0','.25','.5','1']):
                    for L in [None,D(5),D(50)]:
                        p=replace(Parameters(),q=q,v=v,beta=beta,liquidity=L,scale=a,ratio=r)
                        a19=solve_all_output(p);a20=solve_partial(p);x=a20['chosen']
                        rows.append(dict(benchmark=label,q=str(q),v=str(v),beta=str(beta),
                            L='unbounded' if L is None else str(L),channel=x['channel'],
                            y_partial=str(x['y']),z_pool=str(x['z']),y_outside=str(a20['outside']['y']),
                            y_all_output=str(a19['chosen']['y']),profit_partial=str(x['profit']),
                            profit_all_output=str(a19['chosen']['profit']),
                            output_change_vs_outside=str(x['y']-a20['outside']['y']),
                            all_output_change=str(a19['chosen']['y']-a19['outside']['y'])))
    return rows


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='results/gate20')
    args=parser.parse_args()
    root=Path(args.out);root.mkdir(parents=True,exist_ok=True)
    rows=sweep()
    with (root/'partial_pooling_SYNTHETIC.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with localcontext() as ctx:
        ctx.prec=75
        summary=dict(scenarios=len(rows),
                     all_output_lower_output_cases=sum(D(r['all_output_change'])<D('-1e-30') for r in rows),
                     partial_pooling_lower_output_cases=sum(D(r['output_change_vs_outside'])<D('-1e-30') for r in rows),
                     partial_pooling_channel_cases=sum(r['channel']=='partial_pool' for r in rows),
                     producer_profit_dominance_violations=sum(D(r['profit_partial'])+D('1e-30')<D(r['profit_all_output']) for r in rows),
                     scope='synthetic real-formula comparison; not deployed EVM or actual producer behavior')
    (root/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
    p=replace(Parameters(),ratio=D('1.25'),scale=D('.15'),v=D('.55'),beta=D('.25'),c=D('.15'))
    detail=dict(parameters=p.__dict__,outside=solve_partial(p)['outside'],
                all_output=solve_all_output(p)['chosen'],partial=solve_partial(p)['chosen'],
                provenance='same synthetic sufficient-condition example as Gate 19; not mainnet')
    (root/'same_example_SYNTHETIC.json').write_text(json.dumps(detail,indent=2,default=str)+'\n')
    print(json.dumps(summary,indent=2))
    print(json.dumps(detail,indent=2,default=str))


if __name__=='__main__':
    main()
