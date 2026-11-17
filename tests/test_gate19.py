from dataclasses import replace
from decimal import Decimal as D, localcontext
from pathlib import Path
import math
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gate19_endogenous import (Parameters,deposit,domain_bound,liquidity_bound,
                              outside_profit,premium_total,pool_slope,solve)


class EndogenousProductionTests(unittest.TestCase):
    def test_analytic_fee_derivatives_against_finite_differences(self):
        with localcontext() as ctx:
            ctx.prec=65
            for ratio in [D('.99'),D('1.25')]:
                p=replace(Parameters(),ratio=ratio)
                for x in map(D,['1','10','30']):
                    h=D('1e-8')
                    F,first,second=deposit(x,p)
                    fp=deposit(x+h,p);fm=deposit(x-h,p)
                    self.assertLess(abs(first-(fp[0]-fm[0])/(2*h)),D('1e-16'))
                    self.assertLess(abs(second-(fp[1]-fm[1])/(2*h)),D('1e-16'))
                    self.assertGreater(second,0)

    def test_domain_exclusion_and_single_project_exception(self):
        for q in [D(80),D(99)]:
            p=replace(Parameters(),q=q,ratio=D('1.25'))
            self.assertLessEqual(domain_bound(p),0)
            self.assertEqual(solve(p)['chosen']['channel'],'outside')
        p=replace(Parameters(),q=D(100),ratio=D('1.25'))
        self.assertTrue(domain_bound(p).is_infinite())
        self.assertEqual(deposit(D(10),p)[0],1)

    def test_global_solution_against_independent_dense_float_search(self):
        for q,ratio,beta,L in [('0','.99','.5',None),('70','.99','1',None),
                               ('70','1.25','.25',None),('79','1.25','1','5'),
                               ('100','.99','.5','50')]:
            p=replace(Parameters(),q=D(q),ratio=D(ratio),beta=D(beta),
                      liquidity=None if L is None else D(L),v=D('.55'))
            solution=solve(p);Q=float(p.Q);q=float(p.q);r=float(p.ratio)
            limit=min(150.,float(liquidity_bound(p)))
            best=0.
            for i in range(3001):
                y=limit*i/3000
                outside=(float(p.b0)-float(p.c))*y-float(p.k)*y*y/2
                best=max(best,outside)
                if y==0:continue
                if q==Q:F=float(p.single_rate)*y
                elif 1-r*(q+y)/(Q+y)>0:
                    F=float(p.scale)*(q*math.log10(1-r*q/Q)-(q+y)*math.log10(1-r*(q+y)/(Q+y)))
                else:continue
                if not 0<F<=y:continue
                pool=outside+float(p.beta)*max(0.,(1-float(p.v))*y-F-float(p.gas))
                best=max(best,pool)
            self.assertGreaterEqual(float(solution['chosen']['profit'])+1e-11,best)

    def test_pool_profit_can_rise_while_output_falls(self):
        p=replace(Parameters(),ratio=D('1.25'),scale=D('.15'),v=D('.55'),beta=D('.25'),c=D('.15'))
        r=solve(p)
        self.assertGreater(premium_total(r['outside']['y'],p)+p.gas,0)
        self.assertLess(p.P-p.v-p.P*deposit(p.eta*r['outside']['y'],p)[1],0)
        self.assertEqual(r['chosen']['channel'],'pool')
        self.assertGreater(r['chosen']['profit'],r['outside']['profit'])
        self.assertLess(r['chosen']['y'],r['outside']['y'])
        self.assertGreater(r['chosen']['premium'],0)
        self.assertLess(r['chosen']['fee'],p.eta*r['chosen']['y'])

    def test_two_distinct_branch_maxima_can_tie(self):
        p=replace(Parameters(),ratio=D('1.25'),scale=D('.15'),v=D('.55'),beta=D('.25'))
        r=solve(p)
        with localcontext() as ctx:
            ctx.prec=75
            critical=p.gas+r['profit_gap']/p.beta
            tied=solve(replace(p,gas=critical))
        self.assertTrue(tied['numerical_tie'])
        self.assertLess(tied['pool']['y'],tied['outside']['y'])
        self.assertEqual(tied['chosen']['channel'],'outside')

    def test_beta_zero_changes_no_production_but_channel_can_change(self):
        p=replace(Parameters(),q=D(0),v=D('.55'),beta=D(0))
        r=solve(p)
        self.assertEqual(r['chosen']['y'],r['outside']['y'])
        self.assertEqual(r['chosen']['channel'],'pool')

    def test_cash_bound_and_zero_production(self):
        for L in map(D,['0','.1','1','5']):
            p=replace(Parameters(),liquidity=L)
            r=solve(p);y=r['chosen']['y']
            self.assertGreaterEqual(y,0)
            with localcontext() as ctx:
                ctx.prec=75
                self.assertLessEqual(p.c*y+p.k*y*y/2,L+D('1e-60'))
        p=replace(Parameters(),c=D(2))
        self.assertEqual(solve(p)['chosen']['y'],0)

    def test_flat_branch_matches_closed_form_and_fixed_gas_threshold(self):
        p=replace(Parameters(),q=D(100),v=D('.55'),beta=D('.5'))
        r=solve(p)
        expected=(p.eta*(p.b0+p.beta*(p.P-p.v-p.P*p.single_rate))-p.c)/p.k
        self.assertLess(abs(r['pool']['y']-expected),D('1e-50'))
        self.assertEqual(solve(replace(p,gas=D(1000)))['chosen']['channel'],'outside')


if __name__=='__main__':
    unittest.main()
