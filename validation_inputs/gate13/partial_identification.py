#!/usr/bin/env python3
"""Gate 13: partial identification of hypothetical producer output.
No source in this script constitutes observed CHAR transfers, contract beta, or biochar output.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt, inf
import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parent
@dataclass(frozen=True)
class Parameters:
    P:float=200.0
    outside_price:float=155.0
    gas:float=3.0
    transaction_size:float=10.0
    b0:float=140.0
    eta:float=0.8
    c:float=70.0
    k:float=1.1

def premium(fee_rate, p=Parameters()):
    return max(0., p.P*(1-fee_rate)-p.gas/p.transaction_size-p.outside_price)

def cap(L, p=Parameters()):
    if L is None:return inf
    if L < 0: raise ValueError('negative ex ante working capital')
    return (sqrt(p.c**2+2*p.k*L)-p.c)/p.k

def output(beta, fee_rate, L=None, p=Parameters()):
    if not 0<=beta<=1:raise ValueError('beta outside [0,1]')
    return min(cap(L,p),max(0.,(p.eta*(p.b0+beta*premium(fee_rate,p))-p.c)/p.k))

def run():
    rows=[]
    for L in (None,1000.,2500.,5000.):
        for beta in (0.,.25,.5,.75,1.):
            a=output(beta,.10,L)
            b=output(beta,.36,L)
            rows.append(dict(liquidity='unconstrained' if L is None else L,beta=beta,
                fee_single=.10,fee_near=.36,y_single=round(a,6),y_near=round(b,6),
                delta_y=round(a-b,6),source='SYNTHETIC_GATE13'))
    path=ROOT/'synthetic_beta_bounds.csv'
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    assert output(0,.10)==output(0,.36)
    assert abs(output(.5,.10)-47.16363636363636)<1e-10
    assert abs(output(.5,.36)-38.18181818181817)<1e-10
    assert output(.5,.10,1000)==output(.5,.36,1000)
    for L in (None,0,1000,2500,5000):
        for beta in (0,.25,.5,.75,1):
            assert 0<=output(beta,.10,L)-output(beta,.36,L) <= (Parameters().eta/Parameters().k)*beta*(premium(.10)-premium(.36))+1e-9
    print('PASS: 5 identification/feasibility checks; 20 SYNTHETIC scenarios written to',path)
    print('beta unknown, L unconstrained: y(10% fee)-y(36% fee) in [0,',round(output(1,.10)-output(1,.36),5),']')
    return path
if __name__=='__main__':run()
