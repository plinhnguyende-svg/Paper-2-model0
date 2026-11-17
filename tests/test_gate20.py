from dataclasses import replace
from decimal import Decimal as D,localcontext,getcontext
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gate19_endogenous import Parameters,deposit,outside_profit
from gate20_partial_pooling import (gross_gain,optimal_lot_limit,solve_partial,
                                    solve_all_output,batch_fees)


class PartialPoolingTests(unittest.TestCase):
    def setUp(self):
        self.old_precision=getcontext().prec
        getcontext().prec=75

    def tearDown(self):
        getcontext().prec=self.old_precision

    def test_gate19_counterexample_disappears(self):
        p=replace(Parameters(),ratio=D('1.25'),scale=D('.15'),v=D('.55'),beta=D('.25'),c=D('.15'))
        old=solve_all_output(p);new=solve_partial(p)
        self.assertLess(old['chosen']['y'],old['outside']['y'])
        self.assertEqual(new['chosen']['y'],D(35))
        self.assertEqual(new['chosen']['channel'],'partial_pool')
        self.assertLess(new['chosen']['z'],p.eta*new['chosen']['y'])
        self.assertGreater(new['chosen']['profit'],old['chosen']['profit'])

    def test_same_project_batch_potential_telescopes(self):
        with localcontext() as ctx:
            ctx.prec=65
            for ratio,scale,q in [(D('.99'),D('.18'),D(0)),(D('1.25'),D('.15'),D(70)),(D('1.25'),D('.15'),D(100))]:
                p=replace(Parameters(),ratio=ratio,scale=scale,q=q)
                pieces=list(map(D,['.3','1.7','4','2']))
                self.assertLess(abs(batch_fees(p,pieces)-deposit(sum(pieces),p)[0]),D('1e-55'))
                self.assertLess(gross_gain(sum(pieces),p)-len(pieces)*p.gas,
                                gross_gain(sum(pieces),p)-p.gas)

    def test_nested_supply_cap_makes_premium_nondecreasing(self):
        with localcontext() as ctx:
            ctx.prec=65
            p=replace(Parameters(),ratio=D('1.25'),scale=D('.15'),v=D('.55'))
            limit=optimal_lot_limit(p);last=D(0)
            for x in map(D,['.1','1','10','20','30','40','60','100']):
                value=max(D(0),gross_gain(min(x,limit),p)-p.gas)
                self.assertGreaterEqual(value+D('1e-55'),last);last=value

    def test_output_nondecreasing_in_beta_and_outside_floor(self):
        for q in map(D,['0','50','70','79','100']):
            previous=D(0)
            for beta in map(D,['0','.1','.25','.5','1']):
                p=replace(Parameters(),q=q,beta=beta,ratio=D('1.25'),scale=D('.15'),v=D('.55'))
                r=solve_partial(p)
                self.assertGreaterEqual(r['chosen']['y']+D('1e-30'),r['outside']['y'])
                self.assertGreaterEqual(r['chosen']['y']+D('1e-30'),previous)
                previous=r['chosen']['y']

    def test_continuous_solution_beats_independent_joint_grid(self):
        for q in [D(0),D(70),D(79),D(100)]:
            p=replace(Parameters(),q=q,ratio=D('1.25'),scale=D('.15'),v=D('.55'),liquidity=D(50))
            result=solve_partial(p);best=D(0)
            # Independent enumeration of both y and z (not the reduced inner optimizer).
            for i in range(101):
                y=D(i)/2;outside=outside_profit(y,p)
                if p.c*y+p.k*y*y/2>p.liquidity:continue
                best=max(best,outside)
                for j in range(1,31):
                    z=p.eta*y*D(j)/30
                    if z<=0:continue
                    try:F=deposit(z,p)[0]
                    except ValueError:continue
                    if not 0<F<=z:continue
                    best=max(best,outside+p.beta*max(D(0),(p.P-p.v)*z-p.P*F-p.gas))
            self.assertGreaterEqual(result['chosen']['profit']+D('1e-20'),best)

    def test_beta_zero_pooling_does_not_change_output(self):
        p=replace(Parameters(),ratio=D('1.25'),scale=D('.15'),v=D('.55'),beta=D(0))
        r=solve_partial(p)
        self.assertEqual(r['chosen']['y'],r['outside']['y'])
        self.assertEqual(r['chosen']['channel'],'partial_pool')

    def test_no_pool_when_no_spread_or_fixed_cost_too_high(self):
        for p in [replace(Parameters(),v=D('1.1')),replace(Parameters(),gas=D('1000')),
                  replace(Parameters(),q=D(80),ratio=D('1.25'))]:
            self.assertEqual(solve_partial(p)['chosen']['channel'],'outside')

    def test_binding_finance_and_single_project_linear_case(self):
        p=replace(Parameters(),q=D(100),v=D('.55'),liquidity=D(1))
        r=solve_partial(p)
        self.assertEqual(r['chosen']['y'],r['outside']['y'])
        self.assertLessEqual(r['chosen']['z'],p.eta*r['chosen']['y'])
        self.assertEqual(solve_partial(replace(p,liquidity=D(0)))['chosen']['y'],0)


if __name__=='__main__':
    unittest.main()
