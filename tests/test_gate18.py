import sys
import unittest
from decimal import Decimal as D
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gate18_model import (fee, allocate_integer, redemption_allocation, utility,
                          expected_utility, producer, hhi, experiment)


class EconomicRevalidation(unittest.TestCase):
    def test_source_deposit_limit_and_parameter_separation(self):
        almost=fee('deposit',D(100),D(100)+D('1e-12'),D(10))
        self.assertLess(abs(almost-D('3.6')),D('1e-10'))
        self.assertEqual(fee('deposit',D(100),D(100),D(10)),D(1))
        with self.assertRaises(ValueError):
            fee('deposit',D(100),D(101),D(10),scale=D('.15'),ratio=D('1.25'))

    def test_domain_boundary_is_strict_but_single_branch_bypasses(self):
        # (70+50)/(100+50)=0.8 at x=50, so excluded; x=49 is admissible.
        with self.assertRaises(ValueError):
            fee('deposit',D(70),D(100),D(50),scale=D('.15'),ratio=D('1.25'))
        self.assertGreater(fee('deposit',D(70),D(100),D(49),scale=D('.15'),ratio=D('1.25')),0)
        self.assertEqual(fee('deposit',D(100),D(100),D(50),ratio=D('1.25')),D(5))

    def test_fee_ownership_changes_participation(self):
        self.assertLess(utility('deposit',D(10),D(3),D(1),D('.8'),D('.1')),0)
        self.assertGreater(utility('deposit',D(10),D(3),D(1),D('.8'),D('.1'),D('.75')),0)

    def test_integer_allocation_and_redemption_burn_conservation(self):
        self.assertEqual(allocate_integer(7,[75,25]),[6,1])
        for total in range(1,301):
            net,burn=redemption_allocation(total,[75,25],3,10)
            self.assertEqual(sum(net)+burn,total)

    def test_cap_threshold_with_atoms_and_nonunique_optimum(self):
        states=[(D(1),D('.5')),(D(3),D('.5'))]
        # Gross 2, gs=.2, gf=.1, P=1 gives m*=1.9.
        scores={m:expected_utility(states,m,D(2),D(1),D('.2'),D('.1'))
                for m in map(D,['0','1','1.5','1.9','2','3','4'])}
        self.assertEqual(scores[D('1.9')],max(scores.values()))
        self.assertEqual(scores[D(1)],scores[D(2)])
        # Submission is an independent decision: every cap may lose money.
        self.assertLess(expected_utility(states,D(4),D(0),D(1),D('.2'),D('.1')),0)

    def test_hhi_identity_independently_of_fee_formula(self):
        for q in [D(0),D(10),D(50),D(99)]:
            for x in [D('.25'),D(1),D(10)]:
                before=hhi([q,D(100)-q])
                difference=hhi([q+x,D(100)-q])-before
                rhs=(2*D(100)*x*(q/D(100)-before)+x*x*(1-before))/(D(100)+x)**2
                self.assertLess(abs(difference-rhs),D('1e-25'))

    def test_producer_global_optimum_and_bounds(self):
        eta,base,beta,delta,c,k,L=map(D,['.8','140','.5','20','100','2','10000'])
        chosen=producer(eta,base,beta,delta,c,k,L)
        objective=lambda y:eta*(base+beta*delta)*y-c*y-k*y*y/2
        self.assertEqual(chosen,D(10))
        for integer in range(101):
            y=D(integer)/2
            if c*y+k*y*y/2 <= L:
                self.assertGreaterEqual(objective(chosen),objective(y))
        # Positive-output interior derivative only; inactive corner stays zero.
        self.assertEqual(producer(D(1),D(1),D('.5'),D(1),D(10),D(1),D(100)),0)
        y0=producer(eta,base,D(0),D(0),c,k,L)
        self.assertEqual(y0,producer(eta,base,D(0),D(100),c,k,L))
        for beta in map(D,['0','.1','.5','1']):
            y0=producer(eta,base,beta,D(0),c,k,L)
            y1=producer(eta,base,beta,D(30),c,k,L)
            self.assertGreaterEqual(y1-y0,0)
            self.assertLessEqual(y1-y0,eta*beta*D(30)/k)
        self.assertEqual(producer(eta,base,beta,D(30),c,k,D(0)),0)

    def test_finite_policy_search_has_no_omitted_candidate(self):
        rows,certificate=experiment()
        feasible=[r for r in rows if r['feasible']]
        self.assertEqual(len(rows),7)
        self.assertEqual(certificate['scenarios'],36)
        self.assertEqual(D(certificate['optimum_volume']),max(r['volume'] for r in feasible))
        self.assertEqual(set(certificate['winners']),
                         {r['policy'] for r in feasible if r['volume']==D(certificate['optimum_volume'])})


if __name__=='__main__':
    unittest.main()
