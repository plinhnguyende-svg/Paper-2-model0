import unittest
import numpy as np
from gate9_model import (dynamic_deposit_fee,dynamic_redeem_fee,decision_gross,
                         fee_for,read_snapshot,hhi)

class Gate9MathematicalTests(unittest.TestCase):
    def test_single_asset_flat_special_case(self):
        self.assertAlmostEqual(dynamic_deposit_fee(100.,100.,10.),1.)
        self.assertAlmostEqual(dynamic_redeem_fee(100.,100.,10.),1.)

    def test_boundary_noncontinuity(self):
        r=dynamic_redeem_fee(100.,100.01,10.)
        d=dynamic_deposit_fee(100.,100.01,10.)
        self.assertLess(r,1e-6)
        self.assertAlmostEqual(d,3.6,delta=.0002)
        self.assertNotAlmostEqual(r,1.0)

    def test_fee_amounts_snapshot(self):
        _,q=read_snapshot();Q=float(q.sum())
        self.assertAlmostEqual(dynamic_deposit_fee(float(q[0]),Q,10.),.8133907497315102,places=9)
        self.assertAlmostEqual(dynamic_redeem_fee(float(q[-1]),Q,10.),2.70531776927524,places=9)

    def test_ledger_accounting(self):
        x=10.;q=90.;Q=200.;d=dynamic_deposit_fee(q,Q,x)
        alpha=[.7,.3]
        self.assertAlmostEqual((x-d)+sum(a*d for a in alpha),x)
        r=dynamic_redeem_fee(q,Q,x)
        self.assertAlmostEqual((x+r)-sum(a*r for a in alpha),x)

    def test_hhi_mechanical_identity(self):
        _,q=read_snapshot();j=0;x=10.;Q=q.sum();H=hhi(q)
        predicted=(2*Q*x*(q[j]/Q-H)+x*x*(1-H))/(Q+x)**2
        qt=q.copy();qt[j]+=x
        self.assertAlmostEqual(hhi(qt)-H,predicted,places=12)
        predicted_r=(-2*Q*x*(q[j]/Q-H)+x*x*(1-H))/(Q-x)**2
        qt=q.copy();qt[j]-=x
        self.assertAlmostEqual(hhi(qt)-H,predicted_r,places=12)

    def test_payoff_fee_and_rebate_monotonic(self):
        a=decision_gross('deposit',10.,.8,.95,200.,0.)
        b=decision_gross('deposit',10.,.8,.95,200.,.2)
        self.assertAlmostEqual(b-a,200.*.2*.8,places=8)

    def test_conditional_optimal_cap(self):
        # For incremental fee probabilities, accepting yields more than refusing
        # precisely while gross trading benefit >= (g_success - g_failure).
        x=10.;ratio=.95;P=200.;g_s=3.;g_f=2.
        opt=x*(1-ratio)-(g_s-g_f)/P
        for delta in [-.03,-.001,.001,.03]:
            payoff_if_accept=decision_gross('deposit',x,opt+delta,ratio,P)-g_s
            payoff_if_reject=-g_f
            self.assertEqual(payoff_if_accept>=payoff_if_reject,delta<0)

if __name__ == '__main__':unittest.main(verbosity=2)
