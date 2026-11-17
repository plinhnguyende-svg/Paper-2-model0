#!/usr/bin/env python3
"""Finite approved deposit-scale menu with endogenous partial-pooling response."""
from dataclasses import replace
from decimal import Decimal as D,localcontext
from pathlib import Path
import argparse
import csv
import json
from gate19_endogenous import Parameters
from gate20_partial_pooling import solve_partial


def hhi(q,Q,z=D(0)):
    """Two-project inventory only. Gross underlying, not net CHAR mint."""
    return ((q+z)**2+(Q-q)**2)/(Q+z)**2


def lot_concentration_cap(q,Q,maximum):
    H=hhi(q,Q)
    if not H<=maximum<1:
        raise ValueError('require initial HHI <= cap < 1')
    a=1-maximum;b=q-maximum*Q;c=Q*Q*(H-maximum)
    return (-b+(b*b-a*c).sqrt())/a


def design(p,menu,fee_floor=D('.5'),hhi_slack=D('.02')):
    """Single public initial state; owner chooses one scale BEFORE production.
    Fee floor is generic recipient token budget, NOT producer financing.
    """
    if fee_floor<=0 or hhi_slack<0 or not menu or any(not 0<a<=1 for a in menu):
        raise ValueError('invalid normative design inputs')
    with localcontext() as ctx:
        ctx.prec=75
        maximum=hhi(p.q,p.Q)+hhi_slack
        if maximum>=1:
            raise ValueError('example design requires HHI cap <1')
        cap=lot_concentration_cap(p.q,p.Q,maximum)
        rows=[]
        for scale in sorted(set(menu)):
            r=solve_partial(replace(p,scale=scale));c=r['chosen'];z=c['z']
            fee=c.get('fee',D(0));H=hhi(p.q,p.Q,z)
            # Tolerances classify numeric boundary cases; no directed interval claim.
            feasible=(fee+D('1e-40')>=fee_floor and H<=maximum+D('1e-40'))
            rows.append(dict(scale=str(scale),y=str(c['y']),z=str(z),channel=c['channel'],
                             profit=str(c['profit']),fee=str(fee),post_hhi=str(H),
                             fee_budget_pass=fee+D('1e-40')>=fee_floor,
                             composition_pass=H<=maximum+D('1e-40'),feasible=feasible))
        feasible=[r for r in rows if r['feasible']]
        if feasible:
            value=max(D(r['y'])*p.eta for r in feasible)
            winners=[r['scale'] for r in feasible if abs(D(r['y'])*p.eta-value)<=D('1e-35')]
            # Lowest feasible scale is a representative weak optimum by monotonicity.
            selected=min(feasible,key=lambda r:D(r['scale']))
            assert abs(D(selected['y'])*p.eta-value)<=D('1e-35')
        else:
            value=None;winners=[];selected=None
        certificate=dict(status='FINITE_APPROVED_MENU_GLOBAL_ENUMERATION',
                         scales=len(rows),feasible=len(feasible),winners_numeric_tolerance=winners,
                         selected=selected,modeled_certified_output=None if value is None else str(value),
                         initial_hhi=str(hhi(p.q,p.Q)),maximum_hhi=str(maximum),
                         pooling_quantity_cap=str(cap),fee_floor=str(fee_floor),
                         objective='maximize modeled eta*y; not empirical additionality',
                         scope='one known state, fixed beta and ratio; finite scale menu, not functional optimal mechanism',
                         data_status='SYNTHETIC')
        return rows,certificate


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='results/gate21')
    args=parser.parse_args();root=Path(args.out);root.mkdir(parents=True,exist_ok=True)
    menu=[D(i)/100 for i in range(1,31)]
    records=[];certificates=[]
    for label,ratio,baseline in [('S0',D('.99'),D('.18')),
                                  ('H0_parameter_counterfactual',D('1.25'),D('.15'))]:
        for q in [D(10),D(50),D(70)]:
            p=replace(Parameters(),q=q,c=D('.15'),v=D('.55'),beta=D('.25'),ratio=ratio,scale=baseline)
            rows,certificate=design(p,menu)
            for row in rows:records.append(dict(benchmark=label,q=str(q),**row))
            certificate.update(benchmark=label,q=str(q),ratio=str(ratio),baseline_scale=str(baseline))
            certificate['baseline']=next(r for r in rows if D(r['scale'])==baseline)
            certificates.append(certificate)
    with (root/'designer_menu_SYNTHETIC.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    (root/'CERTIFICATES.json').write_text(json.dumps(certificates,indent=2)+'\n')
    print(json.dumps([dict(benchmark=c['benchmark'],q=c['q'],feasible=c['feasible'],
                           selected=c['selected'],pooling_quantity_cap=c['pooling_quantity_cap'])
                      for c in certificates],indent=2))


if __name__=='__main__':
    main()
