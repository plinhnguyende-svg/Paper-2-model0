#!/usr/bin/env python3
"""Gate 18 analytical counterfactuals. No chain data, EVM emulation or price equilibrium."""
from decimal import Decimal, localcontext
from itertools import product
from pathlib import Path
import argparse
import csv
import json

D = Decimal


def fee(kind, current, total, amount, scale=D('.18'), ratio=D('.99'),
        redemption_scale=D('.30'), shift=D('.10'), single=D('.10')):
    """Real-formula quote. Zero/negative/>amount output is infeasible here.
    Decimal cancellation/dust cases are NOT interpreted as EVM dust behavior.
    """
    if kind not in ('deposit', 'redemption'):
        raise ValueError('unknown transaction kind')
    if not (total >= current >= 0 and amount > 0):
        raise ValueError('invalid inventory/amount')
    if kind == 'redemption' and amount > current:
        raise ValueError('insufficient project inventory')
    with localcontext() as ctx:
        ctx.prec = 80
        if current == total:
            result = amount * single
        elif kind == 'deposit':
            before = D(1) - ratio * current / total
            after = D(1) - ratio * (current + amount) / (total + amount)
            if min(before, after) <= 0:
                raise ValueError('dynamic logarithm domain')
            result = scale * (current * before.log10() - (current + amount) * after.log10())
        else:
            a = current / total
            b = (current - amount) / (total - amount)
            result = redemption_scale * ((current - amount) * (b + shift).log10()
                     - current * (a + shift).log10() + amount * (1 + shift).log10())
        if not 0 < result <= amount:
            raise ValueError('real quote nonpositive or exceeds amount; no EVM inference')
        return +result


def allocate_integer(total_fee, percentages):
    """FeeCalculator rounding: first recipient receives division residue."""
    if total_fee < 0 or not percentages or any(x < 0 for x in percentages) or sum(percentages) != 100:
        raise ValueError('invalid fee setup')
    amounts = [total_fee * p // 100 for p in percentages]
    amounts[0] += total_fee - sum(amounts)
    return amounts


def redemption_allocation(total_fee, percentages, burn_numerator, burn_denominator):
    if not 0 <= burn_numerator <= burn_denominator or burn_denominator <= 0:
        raise ValueError('invalid burn fraction')
    gross = allocate_integer(total_fee, percentages)
    burn = [x * burn_numerator // burn_denominator for x in gross]
    return [x-b for x, b in zip(gross, burn)], sum(burn)


def utility(kind, amount, total_fee, price, outside_value, gas, own_fee_fraction=D(0)):
    if not 0 <= own_fee_fraction <= 1 or price <= 0:
        raise ValueError('invalid price or fee ownership')
    if kind == 'deposit':
        return price * (amount - (1-own_fee_fraction) * total_fee) - outside_value * amount - gas
    if kind == 'redemption':
        return outside_value * amount - price * (amount + (1-own_fee_fraction) * total_fee) - gas
    raise ValueError('unknown transaction kind')


def expected_utility(fee_states, cap, gross_surplus, price, success_gas, failure_gas):
    """Baseline disjoint trader/recipients; probabilities must sum to one."""
    if sum(p for _, p in fee_states) != 1 or any(f < 0 or p < 0 for f,p in fee_states):
        raise ValueError('invalid fee distribution')
    return sum(p * (gross_surplus-price*f-success_gas if f <= cap else -failure_gas)
               for f,p in fee_states)


def producer(eta, base, beta, delta, c, k, liquidity):
    if not (eta > 0 and base >= 0 and 0 <= beta <= 1 and delta >= 0 and c >= 0 and k > 0 and liquidity >= 0):
        raise ValueError('invalid producer parameters')
    with localcontext() as ctx:
        ctx.prec = 80
        limit = ((c*c+2*k*liquidity).sqrt()-c)/k
        return min(limit, max(D(0), (eta*(base+beta*delta)-c)/k))


def hhi(inventory):
    total = sum(inventory)
    if not total > 0:
        raise ValueError('HHI undefined for empty inventory')
    return sum((q/total)**2 for q in inventory)


def best_response(scenario, policy):
    """One agent owning a specified project, amount choice, outside payoff zero.
    Tie: abstain at zero, otherwise smallest amount. No sequential market simulation.
    """
    best = dict(amount=D(0), fee=D(0), utility=D(0), hhi=hhi(scenario['inventory']))
    q = scenario['inventory'][scenario['project']]
    total = sum(scenario['inventory'])
    for amount in map(D, ['.25', '1', '2', '5', '10']):
        try:
            if policy['family'] == 'flat':
                quote = policy['rate']*amount
            else:
                quote = fee('deposit', q, total, amount, scale=policy['scale'], ratio=policy['ratio'])
        except ValueError:
            continue
        payoff = utility('deposit', amount, quote, D(1), scenario['outside'], scenario['gas'])
        if payoff > best['utility']:
            after = list(scenario['inventory'])
            after[scenario['project']] += amount
            best = dict(amount=amount, fee=quote, utility=payoff, hhi=hhi(after))
    return best


def experiment():
    # Synthetic scenarios; neither a calibrated panel nor a reachable-state claim.
    scenarios = [dict(inventory=list(map(D, inv)), project=j, outside=D(v), gas=D(g))
                 for inv,j,v,g in product([('50','50'),('99','1'),('100','0')],
                                         [0,1], ['.55','.85','.98'], ['.01','.10'])]
    policies = [dict(name=f'flat_{rate}', family='flat', rate=D(rate))
                for rate in ['.01','.05','.10','.20','.35']]
    policies += [dict(name='source_default_real',family='dynamic',scale=D('.18'),ratio=D('.99')),
                 dict(name='historical_parameter_counterfactual',family='dynamic',scale=D('.15'),ratio=D('1.25'))]
    baseline = [best_response(s, policies[-2]) for s in scenarios]
    rows = []
    for p in policies:
        choices = [best_response(s,p) for s in scenarios]
        # Designer maximizes total volume, with a worst-case concentration constraint
        # and aggregate fee-budget floor. Neither is identified from observed welfare.
        feasible = all(c['hhi'] <= b['hhi']+D('.02') for c,b in zip(choices,baseline))
        feasible &= sum(c['fee'] for c in choices) >= D('.70')*sum(b['fee'] for b in baseline)
        rows.append(dict(policy=p['name'], volume=sum(c['amount'] for c in choices),
                         fees=sum(c['fee'] for c in choices),
                         participant_surplus=sum(c['utility'] for c in choices),
                         worst_hhi_increase=max(c['hhi']-b['hhi'] for c,b in zip(choices,baseline)),
                         feasible=feasible))
    admissible = [r for r in rows if r['feasible']]
    optimum = max(r['volume'] for r in admissible)
    winners = [r['policy'] for r in admissible if r['volume']==optimum]
    return rows, dict(status='FINITE_ENUMERATION_SYNTHETIC', scenarios=len(scenarios),
                      policies=len(policies), amount_actions=6, winners=winners,
                      optimum_volume=str(optimum),
                      arithmetic='Decimal real-formula evaluation; NOT EVM',
                      scope='exhaustive over seven specified policies and six amount choices per independent scenario; no continuum or strategic equilibrium theorem',
                      allocation_design='fixed disjoint recipients; allocation shares are not optimized',
                      constraints={'HHI_increase':'.02','aggregate_fee_floor':'.70'},
                      empirical_effect='NOT_IDENTIFIED')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', default='results/gate18')
    args = p.parse_args()
    root=Path(args.out)
    root.mkdir(parents=True,exist_ok=True)
    rows, certificate=experiment()
    with (root/'policy_search_SYNTHETIC.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
    (root/'finite_search_certificate.json').write_text(json.dumps(certificate,indent=2)+'\n')
    print(json.dumps(certificate,indent=2))


if __name__=='__main__':
    main()
