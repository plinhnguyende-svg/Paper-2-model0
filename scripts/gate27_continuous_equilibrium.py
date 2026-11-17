#!/usr/bin/env python3
"""Gate 27: analytical inverse scale-to-output map for an interior active equilibrium.

This module is an EXACT algebraic reduction under Gate 20's real formula,
not EVM integer arithmetic, contract calibration, or a claim of global
continuous mechanism optimality. It returns a conditional equilibrium
candidate and verifies it with the independently implemented Gate20 solver.
"""
from dataclasses import replace
from decimal import Decimal as D, localcontext
from pathlib import Path
import argparse
import json

from gate19_endogenous import (
    Parameters, validate, liquidity_bound, domain_bound, deposit, outside_profit
)
from gate20_partial_pooling import solve_partial
from gate21_designer import hhi, lot_concentration_cap


def outside_output(p):
    validate(p)
    return min(liquidity_bound(p),
               max(D(0), (p.eta*p.b0-p.c)/p.k))


def inverse_active_scale(p, y):
    """Exact algebraic inversion of producer FOC, at interior unsaturated z=eta*y.

    k*y = eta*b0-c+beta*eta*(P-v-P*a*f'(eta*y)).
    => a(y)= [eta*b0-c+beta*eta*(P-v)-k*y] /
              [beta*eta*P*f'(eta*y)].
    f=F at unit scale. Strictly decreases with y on positive-a branch
    since f'>0 and f''>0; can fail at a branch boundary.
    """
    validate(p)
    if p.q >= p.Q or p.beta <= 0 or y <= 0:
        raise ValueError("inverse requires a multi-project state with beta>0 and y>0")
    if y <= outside_output(p):
        raise ValueError("strictly expanded interior equilibrium only")
    if y >= liquidity_bound(p):
        raise ValueError("liquidity boundary cannot be inverted as interior FOC")
    if y*p.eta >= domain_bound(p)*p.eta:
        raise ValueError("outside dynamic domain")
    unit = replace(p, scale=D(1))
    _, fprime, fsecond = deposit(p.eta*y, unit)
    if not fprime > 0 or not fsecond > 0:
        raise ValueError("requires strictly convex smooth deposit fee")
    numerator = p.eta*p.b0-p.c+p.beta*p.eta*(p.P-p.v)-p.k*y
    if numerator <= 0:
        raise ValueError("nonpositive candidate scale")
    a = numerator/(p.beta*p.eta*p.P*fprime)
    if not 0<a<=1:
        raise ValueError("candidate scale outside positive permitted interval")
    return a


def evaluate_inverse(p, y, budget=D(".5"), hhi_slack=D(".02")):
    """Check incentives, execution, and designer constraints separately."""
    with localcontext() as ctx:
        ctx.prec=75
        a=inverse_active_scale(p,y)
        candidate=replace(p,scale=a)
        z=p.eta*y
        fee,marginal,curvature=deposit(z,candidate)
        gross=(p.P-p.v)*z-p.P*fee
        surplus=gross-p.gas
        outside_y=outside_output(p)
        outside_value=outside_profit(outside_y,p)
        active_value=outside_profit(y,p)+p.beta*surplus
        maximum_hhi=hhi(p.q,p.Q)+hhi_slack
        if maximum_hhi>=1:
            raise ValueError("HHI ceiling must remain strictly below one")
        lot_cap=lot_concentration_cap(p.q,p.Q,maximum_hhi)
        selected=solve_partial(candidate)["chosen"]
        same_selected=(selected['channel']!='outside'
                       and abs(selected['y']-y) <=D("1e-35")
                       and abs(selected['z']-z) <=D("1e-35"))
        return dict(
            y=str(y),scale=str(a),z=str(z),
            fee=str(fee),marginal_fee=str(marginal),fee_curvature=str(curvature),
            gross_premium=str(gross),net_premium=str(surplus),
            producer_active_payoff=str(active_value),producer_outside_payoff=str(outside_value),
            equilibrium_conditions=dict(
                calculator_fee_positive=fee>0,
                calculator_fee_below_gross_deposit=fee<z,
                gross_pooling_margin_positive=(p.P-p.v-p.P*marginal)>0,
                intermediary_pooling_vs_outside=surplus>0,
                producer_global_active_choice=active_value>outside_value,
                gate20_solver_confirms_active_quantity=same_selected
            ),
            design_conditions=dict(
                hhi_after=str(hhi(p.q,p.Q,z)),
                hhi_max=str(maximum_hhi),
                hhi_cap_lot=str(lot_cap),
                hhi_pass=z<=lot_cap,
                token_budget=str(budget),
                budget_pass=fee>=budget
            ),
            scope="CONDITIONAL_INTERIOR_REAL_FORMULA_NO_EVM_NO_PRODUCER_ATTRIBUTION"
        )


def example():
    with localcontext() as ctx:
        ctx.prec=75
        p=replace(Parameters(),q=D(10),v=D(".55"),c=D(".15"),
                  beta=D(".25"),ratio=D("1.25"),scale=D(".05"),
                  liquidity=None)
        r=solve_partial(p)
        y=r["chosen"]["y"]
        row=evaluate_inverse(p,y)
        # Show a *local* continuous fee-budget boundary between .04 and .05.
        # Feasibility outside the bracket is NOT certified.
        left,right=D(".04"),D(".05")
        def fee_at(a):
            chosen=solve_partial(replace(p,scale=a))["chosen"]
            return chosen.get("fee",D(0))
        if not (fee_at(left)<D(".5")<=fee_at(right)):
            raise ArithmeticError("selected scenario does not bracket budget")
        for _ in range(85):
            mid=(left+right)/2
            if fee_at(mid)>=D(".5"):
                right=mid
            else:
                left=mid
        threshold=right
        selected=solve_partial(replace(p,scale=threshold))["chosen"]
        return dict(
            parameters={k:str(v) for k,v in p.__dict__.items()},
            source_model="real fee source formula; historical .15/1.25 configuration as model substitution",
            inverted_active_equilibrium=row,
            local_budget_boundary=dict(
                scale=str(threshold),fee=str(selected.get("fee",D(0))),
                production=str(selected["y"]),channel=selected["channel"],
                bracket=["0.04","0.05"],nominal_floor="0.5",
                caveat="local bracket and numerical bisection only; not full real-scale global optimum"
            )
        )


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="results/gate27")
    args=p.parse_args()
    root=Path(args.out);root.mkdir(parents=True,exist_ok=True)
    data=example()
    (root/"CONDITIONAL_EQUILIBRIUM_SYNTHETIC.json").write_text(
        json.dumps(data,indent=2)+"\n")
    print(json.dumps(data,indent=2))


if __name__ == "__main__":
    main()
