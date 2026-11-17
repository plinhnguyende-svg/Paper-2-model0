from dataclasses import replace
from decimal import Decimal as D,getcontext
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gate19_endogenous import Parameters
from gate20_partial_pooling import solve_partial,optimal_lot_limit,gross_gain
from gate21_designer import design,hhi,lot_concentration_cap


class DesignerTests(unittest.TestCase):
    def setUp(self):
        self.prec=getcontext().prec;getcontext().prec=75
        self.menu=[D(i)/100 for i in range(1,31)]

    def tearDown(self):
        getcontext().prec=self.prec

    def test_hhi_quadratic_cap_matches_direct_inventory(self):
        for q in map(D,['10','50','70']):
            maximum=hhi(q,D(100))+D('.02')
            z=lot_concentration_cap(q,D(100),maximum)
            self.assertLess(abs(hhi(q,D(100),z)-maximum),D('1e-60'))
            self.assertLessEqual(hhi(q,D(100),z/2),maximum)
            self.assertGreater(hhi(q,D(100),z+D('.01')),maximum)

    def test_minority_project_budget_limits_low_fee(self):
        p=replace(Parameters(),q=D(10),c=D('.15'),v=D('.55'),beta=D('.25'))
        rows,c=design(p,self.menu)
        self.assertEqual(c['selected']['scale'],'0.05')
        self.assertFalse(next(r for r in rows if D(r['scale'])==D('.04'))['fee_budget_pass'])
        selected=next(r for r in rows if D(r['scale'])==D('.05'))
        self.assertTrue(selected['feasible'])
        self.assertGreater(D(selected['y']),D(35))
        self.assertLess(D(next(r for r in rows if D(r['scale'])==D('.06'))['y']),D(selected['y']))

    def test_selected_lowest_feasible_scale_maximizes_menu_output(self):
        for q,r in [(D(10),D('.99')),(D(10),D('1.25')),(D(70),D('1.25'))]:
            p=replace(Parameters(),q=q,ratio=r,c=D('.15'),v=D('.55'),beta=D('.25'))
            rows,c=design(p,self.menu)
            feasible=[r for r in rows if r['feasible']]
            self.assertEqual(D(c['selected']['scale']),min(D(r['scale']) for r in feasible))
            for other in feasible:
                self.assertGreaterEqual(D(c['selected']['y'])+D('1e-35'),D(other['y']))

    def test_concentration_cap_can_block_all_production_expansion(self):
        p=replace(Parameters(),q=D(70),ratio=D('1.25'),c=D('.15'),v=D('.55'),beta=D('.25'))
        rows,c=design(p,self.menu)
        self.assertLess(D(c['pooling_quantity_cap']),D(35))
        self.assertEqual(c['feasible'],2)
        for r in rows:
            if r['feasible']:
                self.assertEqual(D(r['y']),D(35))

    def test_premium_has_increasing_differences_when_scale_falls(self):
        for q,ratio in [(D(10),D('.99')),(D(70),D('1.25'))]:
            low=replace(Parameters(),q=q,ratio=ratio,scale=D('.05'),v=D('.55'))
            high=replace(low,scale=D('.20'))
            zl=optimal_lot_limit(low);zh=optimal_lot_limit(high)
            previous=D(0)
            for y in map(D,['0','1','5','10','20','40','80']):
                Vl=max(D(0),gross_gain(min(low.eta*y,zl),low)-low.gas)
                Vh=max(D(0),gross_gain(min(high.eta*y,zh),high)-high.gas)
                self.assertGreaterEqual(Vl-Vh+D('1e-50'),previous)
                previous=Vl-Vh

    def test_recipient_fee_revenue_is_not_assumed_monotone(self):
        p=replace(Parameters(),q=D(70),ratio=D('1.25'),c=D('.15'),v=D('.55'),beta=D('.25'))
        values=[solve_partial(replace(p,scale=a))['chosen'].get('fee',D(0)) for a in map(D,['.01','.15','.30'])]
        self.assertLess(values[0],values[1]);self.assertEqual(values[2],0)

    def test_no_feasible_policy_is_reported_without_forcing_producer_exit(self):
        p=replace(Parameters(),q=D(50),c=D('.15'),v=D('.55'),beta=D('.25'))
        _,c=design(p,self.menu)
        self.assertEqual(c['feasible'],0);self.assertIsNone(c['selected'])
        self.assertGreater(solve_partial(p)['chosen']['y'],0)

    def test_budget_and_cap_inputs_are_explicit_constraints(self):
        with self.assertRaises(ValueError):design(Parameters(),self.menu,fee_floor=D(0))
        with self.assertRaises(ValueError):design(Parameters(),[D(0)])
        with self.assertRaises(ValueError):lot_concentration_cap(D(70),D(100),D('.50'))


if __name__=='__main__':
    unittest.main()
