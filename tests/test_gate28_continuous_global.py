"""Gate 28 continuous, full-domain solver and regime tests (synthetic).
Tests distinguish globally covered parameter space from numerical epsilon certificates.
"""
from dataclasses import replace
from decimal import Decimal as D, getcontext
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "scripts"))
from gate19_endogenous import Parameters, liquidity_bound
from gate20_partial_pooling import solve_partial
from gate28_continuous_global import (
    ContinuousDesigner, classify, possible_max_output
)


class Gate28Tests(unittest.TestCase):
    def setUp(self):
        self.prec = getcontext().prec
        getcontext().prec = 70
        self.base = replace(Parameters(), q=D(10), c=D(".15"),
                            v=D(".55"), beta=D(".25"),
                            ratio=D("1.25"), scale=D(".05"))
    def tearDown(self):
        getcontext().prec = self.prec

    def test_total_domain_output_bound_on_sampled_continuous_scales(self):
        bound=possible_max_output(self.base)
        for a in [D(".0001"),D(".01"),D(".05"),D(".2"),D(".5"),D("1")]:
            y=solve_partial(replace(self.base,scale=a))["chosen"]["y"]
            self.assertLessEqual(y,bound+D("1e-35"))

    def test_outside_regime(self):
        p=replace(self.base,v=D(1))
        r=solve_partial(p)["chosen"]
        self.assertEqual(classify(p,r),"NO_POOL_OUTSIDE")
        self.assertEqual(r["z"],0)

    def test_liquidity_binding_regime(self):
        p=replace(self.base,liquidity=D(5))
        r=solve_partial(p)["chosen"]
        self.assertEqual(classify(p,r),"POOL_LIQUIDITY_BINDING")
        self.assertLessEqual(r["y"],liquidity_bound(p))

    def test_saturated_lot_regime(self):
        p=replace(self.base,q=D(70),scale=D(".21"))
        r=solve_partial(p)["chosen"]
        self.assertEqual(classify(p,r),"POOL_SATURATED_LOT")
        self.assertLess(r["z"],p.eta*r["y"])

    def test_unsaturated_regime(self):
        r=solve_partial(self.base)["chosen"]
        self.assertEqual(classify(self.base,r),"POOL_UNSATURATED_SUPPLY_BINDING")
        self.assertEqual(r["z"],r["y"])

    def test_interval_fee_upper_bound_contains_endpoints(self):
        engine=ContinuousDesigner(self.base)
        for left,right in [(D(".01"),D(".03")),(D(".03"),D(".04")),
                           (D(".15"),D(".30"))]:
            bound=engine.fee_upper(left,right)
            self.assertGreaterEqual(bound+D("1e-25"),engine.at(left)["fee"])
            self.assertGreaterEqual(bound+D("1e-25"),engine.at(right)["fee"])

    def test_chosen_quantity_and_lot_are_weakly_decreasing_in_scale(self):
        engine=ContinuousDesigner(self.base)
        rows=[engine.at(a) for a in
              [D(".01"),D(".03"),D(".04"),D(".07"),D(".12"),D(".25"),D(".6"),D("1")]]
        for l,r in zip(rows,rows[1:]):
            self.assertGreaterEqual(l["y"]+D("1e-35"),r["y"])
            self.assertGreaterEqual(l["z"]+D("1e-35"),r["z"])

    def test_continuous_scoped_global_bracket_beats_30_step_menu(self):
        engine=ContinuousDesigner(self.base,tolerance=D(".00001"),max_nodes=1700)
        c=engine.solve()
        self.assertEqual(c["status"],"MONOTONE_GLOBAL_TO_NUMERIC_SCALE_BRACKET")
        self.assertLessEqual(D(c["scale_gap_numeric"]),D(".00001"))
        self.assertLess(D(c["best_feasible_scale_numeric"]),D(".04"))
        self.assertGreater(D(c["modeled_output_at_feasible_scale"]),D("45.72"))
        self.assertTrue(c["selected_feasible"]["is_feasible"])

    def test_budget_and_hhi_are_both_checked(self):
        engine=ContinuousDesigner(self.base)
        self.assertFalse(engine.at(D(".01"))["is_feasible"])
        self.assertTrue(engine.at(D(".04"))["is_feasible"])
        self.assertLess(engine.zcap,engine.z_upper*D(100))

    def test_zero_liquidity_makes_positive_budget_infeasible(self):
        engine=ContinuousDesigner(replace(self.base,liquidity=D(0)),
                                   tolerance=D(".00001"),max_nodes=200)
        c=engine.solve()
        self.assertEqual(c["status"],"NO_FEASIBLE_CONTINUOUS_POLICY_BOUNDED_NUMERIC_EXCLUSIONS")
        self.assertIsNone(c["best_feasible_scale_numeric"])

    def test_analytic_global_no_pooling_under_hhi_cap_s0_q70(self):
        p=replace(self.base,q=D(70),ratio=D(".99"),scale=D(".18"))
        cert=ContinuousDesigner(p).solve()
        self.assertEqual(cert["status"],
                         "ANALYTIC_GLOBAL_INFEASIBLE_HHI_VS_PARTICIPATION")
        proof=cert["structural_infeasibility"]
        self.assertTrue(proof["global_infeasible"])
        self.assertGreater(D(proof["outside_supply"]),D(proof["HHI_lot_cap"]))
        self.assertLess(D(proof["critical_net_gain"]),0)

    def test_same_hhi_conflict_not_falsely_applied_to_h0_q70(self):
        p=replace(self.base,q=D(70),ratio=D("1.25"),scale=D(".15"))
        engine=ContinuousDesigner(p)
        t=engine.structural_infeasibility()
        self.assertFalse(t["global_infeasible"])
        self.assertGreater(D(t["critical_net_gain"]),0)

    def test_bad_fee_budget_rejected(self):
        with self.assertRaises(ValueError):
            ContinuousDesigner(self.base,budget=D(0))

if __name__=="__main__":
    unittest.main()
