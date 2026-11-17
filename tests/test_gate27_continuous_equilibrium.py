"""Gate 27 mathematical inverse and local conditional equilibrium tests."""
from dataclasses import replace
from decimal import Decimal as D, getcontext
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from gate19_endogenous import Parameters
from gate20_partial_pooling import solve_partial
from gate27_continuous_equilibrium import (
    inverse_active_scale, evaluate_inverse, outside_output
)


class Gate27InverseTests(unittest.TestCase):
    def setUp(self):
        self.prec = getcontext().prec
        getcontext().prec = 75
        self.p = replace(Parameters(), q=D(10), v=D(".55"), c=D(".15"),
                         beta=D(".25"), ratio=D("1.25"), scale=D(".05"),
                         liquidity=None)
    def tearDown(self):
        getcontext().prec=self.prec

    def test_inverse_recovers_actual_source_formula_scale(self):
        chosen=solve_partial(self.p)["chosen"]
        self.assertNotEqual(chosen["channel"],"outside")
        recovered=inverse_active_scale(self.p,chosen["y"])
        self.assertLess(abs(recovered-self.p.scale),D("1e-50"))

    def test_interior_inverse_strictly_decreasing_in_production(self):
        y=solve_partial(self.p)["chosen"]["y"]
        a=inverse_active_scale(self.p,y)
        higher=inverse_active_scale(self.p,y+D(".01"))
        self.assertLess(higher,a)

    def test_synthetic_candidate_satisfies_real_incentives_and_design(self):
        y=solve_partial(self.p)["chosen"]["y"]
        c=evaluate_inverse(self.p,y)
        self.assertTrue(all(c["equilibrium_conditions"].values()))
        self.assertTrue(all(c["design_conditions"][k] for k in ("hhi_pass","budget_pass")))

    def test_no_beta_cannot_invert(self):
        with self.assertRaises(ValueError):
            inverse_active_scale(replace(self.p,beta=D(0)),D(40))

    def test_outside_output_not_an_interior_expansion(self):
        with self.assertRaises(ValueError):
            inverse_active_scale(self.p,outside_output(self.p))

    def test_cash_binding_is_not_interior(self):
        limited=replace(self.p,liquidity=D(5))
        with self.assertRaises(ValueError):
            inverse_active_scale(limited,D(100))

    def test_single_project_not_dynamic_interior(self):
        with self.assertRaises(ValueError):
            inverse_active_scale(replace(self.p,q=D(100)),D(45))


if __name__ == "__main__":
    unittest.main()
