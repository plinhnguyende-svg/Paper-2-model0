#!/usr/bin/env python3
"""Gate 28: continuous designer search with global monotone response bounds.

Operates on the Gate 20 REAL-FORMULA partial-allocation model, not EVM integers.
It partitions the WHOLE scale domain (0,1], with a zero-endpoint analytic
upper bound. Uses interval enclosure arguments based on monotone endogenous
y(a), z(a), and monotone unit-scale f(z). Numerical Decimal evaluations are
not directed interval arithmetic; precision qualification is explicit.
"""
import argparse
import heapq
import json
from dataclasses import replace
from decimal import Decimal as D, localcontext
from pathlib import Path

from gate19_endogenous import Parameters, deposit, domain_bound, liquidity_bound, validate
from gate20_partial_pooling import solve_partial, marginal_gain
from gate21_designer import design, hhi, lot_concentration_cap

GUARD = D("1e-30")
NUMERIC_Z_ENLARGEMENT = D("1e-24")


def possible_max_output(p):
    """Analytical upper bound on every producer optimum at any a>0.

    V'(y) <= eta*(P-v) when V is active; U_out'(y) decreases as -k*y.
    Also imposes the pre-processing cash cap. This is a global output bound,
    not an equilibrium at a=0.
    """
    return min(liquidity_bound(p), max(D(0),
               (p.eta*p.b0-p.c+p.beta*p.eta*(p.P-p.v))/p.k))


def classify(p, row):
    a = row["channel"]
    if a == "outside":
        return "NO_POOL_OUTSIDE"
    y, z = row["y"], row["z"]
    cap = liquidity_bound(p)
    if cap.is_finite() and abs(y-cap) <= D("1e-40"):
        return "POOL_LIQUIDITY_BINDING"
    if z < p.eta*y-D("1e-40"):
        return "POOL_SATURATED_LOT"
    if marginal_gain(z,p) <= D("1e-40"):
        return "POOL_LOT_STATIONARY_BOUNDARY"
    return "POOL_UNSATURATED_SUPPLY_BINDING"


class ContinuousDesigner:
    def __init__(self, params, budget=D(".5"), slack=D(".02"),
                 tolerance=D(".000001"), max_nodes=2400):
        validate(params)
        if not (params.q < params.Q and params.q >= 0
                and budget > 0 and slack >= 0 and tolerance > 0
                and 10 <= max_nodes <= 100000):
            raise ValueError("invalid Gate28 continuous-design specification")
        self.p = params
        self.budget = budget
        self.tolerance = tolerance
        self.max_nodes = max_nodes
        self.max_hhi = hhi(params.q,params.Q)+slack
        if self.max_hhi >= 1:
            raise ValueError("requires HHI ceiling below one")
        self.zcap = lot_concentration_cap(params.q, params.Q, self.max_hhi)
        self.y_upper = possible_max_output(params)
        self.z_upper = params.eta*self.y_upper
        self.cache = {}
        self.counters = dict(intervals_examined=0, excluded_budget=0,
                             excluded_hhi=0, nodes_split=0,
                             point_evaluations=0, approximate_unresolved=0,
                             feasible_samples=0, explored_all_scales=False,
                             budget_upper_at_zero="UNSET")
        self.unit=replace(params,scale=D(1))

    def unit_fee(self, z):
        if z <= 0:
            return D(0)
        return deposit(z,self.unit)[0]

    def at(self,a):
        if not 0<a<=1:
            raise ValueError("a must be in (0,1]")
        a=+a
        if a in self.cache:
            return self.cache[a]
        p=replace(self.p,scale=a)
        solution=solve_partial(p)
        r=solution["chosen"]
        y,z=r["y"],r["z"]
        fee=r.get("fee",D(0))
        row=dict(scale=a, y=y,z=z,fee=fee,channel=r["channel"],
                 regime=classify(p,r),
                 post_hhi=hhi(p.q,p.Q,z),
                 is_feasible=(fee>=self.budget+GUARD and
                              z<=self.zcap-GUARD),
                 exact_budget_gap=fee-self.budget,
                 exact_composition_gap=self.zcap-z)
        self.cache[a]=row
        self.counters["point_evaluations"]+=1
        return row

    def upper_z(self,left):
        if left==0:
            return self.z_upper
        return self.at(left)["z"]+NUMERIC_Z_ENLARGEMENT

    def fee_upper(self,left,right):
        zmax=self.upper_z(left)
        bound=domain_bound(self.p)*self.p.eta
        if bound.is_finite() and zmax >= bound:
            return D("Infinity")
        return right*self.unit_fee(zmax)

    def box_exclusion(self,left,right):
        # In this region y and chosen z are weakly nonincreasing in a.
        # z(a) >= z(right), so HHI rejection is certifiable from right.
        if self.at(right)["z"] > self.zcap+GUARD:
            self.counters["excluded_hhi"]+=1
            return "HHI"
        # F(a)=a*f(z(a)) <= right*f(z(left)), where z(0) is bounded
        # by the analytical maximal output, not evaluated as an EVM action.
        if self.fee_upper(left,right) < self.budget-GUARD:
            self.counters["excluded_budget"]+=1
            return "FEE_BUDGET"
        return None

    def find_seed(self):
        # Deterministic rational samples spanning full admissible interval;
        # lack of a sample never implies global infeasibility.
        for i in range(1,101):
            row=self.at(D(i)/100)
            if row["is_feasible"]:
                return row["scale"]
        return None

    def structural_infeasibility(self):
        """Global theorem: inventory cap conflicts with pooling activation.

        Assume eta*y_out > z_cap and dynamic f is smooth at z_cap.
        Define a_c=(P-v)/(P*f'(z_cap)).
        For a<a_c, G'_a(z_cap)>0. The intermediary's optimal lot
        exceeds z_cap whenever pooling activates, since eta*y>=eta*y_out
        by Gate20 output floor. Hence HHI fails.
        For a>=a_c, G_a(z)<=G_{a_c}(z_cap) for every z because
        G_a is pointwise decreasing in a, and G_{a_c} has its unique
        maximum at z_cap. If this gross gain <=gas, pooling cannot
        activate. At tie the declared outside rule applies.
        If a_c>1, all admissible a fail the HHI condition whenever active.
        """
        p=self.p
        y0=solve_partial(p)["outside"]["y"]
        if p.P<=p.v:
            return dict(reason="P_NOT_ABOVE_OUTSIDE", global_infeasible=True,
                        observation="gross pooling gain cannot exceed gas")
        if not p.eta*y0 > self.zcap+GUARD:
            return dict(reason="NOT_APPLICABLE_OUTSIDE_SUPPLY_BELOW_HHI_CAP",
                        global_infeasible=False)
        limit=domain_bound(p)*p.eta
        if limit.is_finite() and self.zcap >= limit:
            return dict(reason="NOT_APPLICABLE_HHI_CAP_OUTSIDE_LOG_DOMAIN",
                        global_infeasible=False)
        unit_fee,unit_marginal,_=deposit(self.zcap,self.unit)
        if unit_marginal<=0:
            return dict(reason="NOT_APPLICABLE_NONPOSITIVE_UNIT_MARGINAL",
                        global_infeasible=False)
        ac=(p.P-p.v)/(p.P*unit_marginal)
        gross=(p.P-p.v)*self.zcap-p.P*ac*unit_fee
        condition=(ac>1+GUARD or (ac<=1 and gross < p.gas-GUARD))
        return dict(
            global_infeasible=condition,
            reason=("HHI_VS_PARTICIPATION_NO_OVERLAP" if condition
                    else "STRUCTURAL_TEST_DOES_NOT_EXCLUDE_FEASIBILITY"),
            outside_supply=str(p.eta*y0), HHI_lot_cap=str(self.zcap),
            critical_scale=str(ac), critical_gross_gain_before_gas=str(gross),
            gas=str(p.gas), critical_net_gain=str(gross-p.gas),
            all_scale_domain="(0,1]",
            math_status="global sufficient condition, numerical strict inequalities")

    def solve(self):
        with localcontext() as ctx:
            ctx.prec=70
            theorem=self.structural_infeasibility()
            if theorem["global_infeasible"]:
                return dict(
                    status="ANALYTIC_GLOBAL_INFEASIBLE_HHI_VS_PARTICIPATION",
                    benchmark_scope="Gate20 fixed-state real fee; not EVM",
                    feasible_scale=None, selected_feasible=None,
                    smallest_feasible_scale_lower_bound_numeric=None,
                    best_feasible_scale_numeric=None,
                    scale_gap_numeric=None,
                    modeled_output_at_feasible_scale=None,
                    fee_budget=str(self.budget),
                    HHI_cap=str(self.max_hhi),lot_cap=str(self.zcap),
                    outside_y=str(solve_partial(self.p)["outside"]["y"]),
                    structural_infeasibility=theorem,
                    sampled_regimes=["NO_POOL_OR_HHI_VIOLATION"],
                    counters=self.counters,
                    qualifications=[
                        "Analytical sufficient condition checks all a in (0,1]",
                        "Strict numerical inequalities checked with 70-digit Decimal, not formal interval arithmetic",
                        "Positive fee budget is impossible without pooling; conditional contract and price assumptions"
                    ])
            seed=self.find_seed()
            best=seed
            heap=[(D(0),best if best is not None else D(1))]
            earliest_unresolved=None
            gap_tolerance=D(self.tolerance)
            terminal_cells=[]
            while heap and self.counters["intervals_examined"] < self.max_nodes:
                left,right=heapq.heappop(heap)
                if best is not None and left>=best:
                    continue
                if best is not None and right>best:
                    right=best
                if right<=left:
                    continue
                self.counters["intervals_examined"]+=1
                reason=self.box_exclusion(left,right)
                if reason:
                    continue
                if right-left<=gap_tolerance:
                    earliest_unresolved=left
                    terminal_cells.append(dict(left=str(left),right=str(right),
                                               reason="bounds overlap constraints at numeric precision"))
                    self.counters["approximate_unresolved"]+=1
                    break  # heap is ordered by increasing left; no earlier unknown interval
                mid=(left+right)/2
                point=self.at(mid)
                if point["is_feasible"] and (best is None or mid<best):
                    best=mid
                    self.counters["feasible_samples"]+=1
                heapq.heappush(heap,(left,mid))
                heapq.heappush(heap,(mid,right))
                self.counters["nodes_split"]+=1
            self.counters["explored_all_scales"]=not heap and earliest_unresolved is None
            if best is None:
                if self.counters["explored_all_scales"]:
                    status="NO_FEASIBLE_CONTINUOUS_POLICY_BOUNDED_NUMERIC_EXCLUSIONS"
                else:
                    status="NO_FEASIBLE_POINT_FOUND_GLOBAL_SEARCH_UNRESOLVED"
                lower=None
            elif earliest_unresolved is not None:
                status="MONOTONE_GLOBAL_TO_NUMERIC_SCALE_BRACKET"
                lower=earliest_unresolved
            elif self.counters["explored_all_scales"]:
                status="GLOBAL_FEASIBLE_SCALE_IDENTIFIED_WITH_NUMERIC_BOUNDS"
                lower=best
            else:
                status="FEASIBLE_POLICY_FOUND_GLOBAL_CERTIFICATE_UNRESOLVED"
                lower=None
            record = {
                "status":status, "model":"Gate20 real formula with Gate28 continuous-scale bounds",
                "scope":"entire fee-scale domain (0,1], fixed state and fixed contractual beta",
                "direction":"smallest feasible a yields maximal modeled output (weakly, due plateaus)",
                "max_scale": "1", "requested_numeric_resolution":str(self.tolerance),
                "smallest_feasible_scale_lower_bound_numeric":None if lower is None else str(lower),
                "best_feasible_scale_numeric":None if best is None else str(best),
                "scale_gap_numeric":None if lower is None or best is None else str(best-lower),
                "selected_feasible":None if best is None else self._serialize_row(self.at(best)),
                "outside_y":str(solve_partial(self.p)["outside"]["y"]),
                "possible_max_output_upper_bound":str(self.y_upper),
                "HHI_cap":str(self.max_hhi),"lot_cap":str(self.zcap),
                "fee_budget":str(self.budget),
                "counters":self.counters,
                "qualifications": [
                    "Numerical Decimal/root-bisection bounds, not formally directed interval arithmetic",
                    "Unscanned or unresolved intervals are never called infeasible",
                    "Not all governance functions, prices, contractual beta, or EVM rounding",
                    "A near-optimal scale bracket is not a proof of unique scale or unique outcome",
                ],
                "boundary_cells":terminal_cells,
                "structural_infeasibility":theorem,
                "sampled_regimes":sorted(set(x["regime"] for x in self.cache.values())),
            }
            if best is not None and lower is not None:
                # Under the Gate21 proved monotonic output response,
                # selected output at lower is an upper bound on attainable output.
                if lower>0:
                    record["modeled_output_upper_at_scale_lower_numeric"]=str(self.at(lower)["y"])
                record["modeled_output_at_feasible_scale"]=str(self.at(best)["y"])
            return record

    @staticmethod
    def _serialize_row(r):
        return {k:str(v) if isinstance(v,D) else v for k,v in r.items()}


def study():
    with localcontext() as ctx:
        ctx.prec=70
        data=[]
        for ratio_name,ratio,baseline in [
            ("S0_source",D(".99"),D(".18")),
            ("H0_historical_config_counterfactual",D("1.25"),D(".15"))
        ]:
            for q in [D(10),D(50),D(70)]:
                p=replace(Parameters(),q=q,c=D(".15"),v=D(".55"),
                          beta=D(".25"),ratio=ratio,scale=baseline)
                engine=ContinuousDesigner(p)
                cert=engine.solve()
                cert.update(benchmark=ratio_name, q=str(q),
                            contractual_beta_assumed=str(p.beta),
                            initial_scale_reference=str(baseline),
                            initial_reference_regime=engine.at(baseline)["regime"])
                # The Gate21 discrete benchmark is for comparison ONLY.
                _, menu=design(p,[D(i)/100 for i in range(1,31)])
                cert["gate21_menu_selected"]=None if menu["selected"] is None else menu["selected"]["scale"]
                data.append(cert)
        return data


def robustness():
    """Regime coverage beyond unbounded-liquidity positive-pass-through grid."""
    with localcontext() as ctx:
        ctx.prec=70
        base=replace(Parameters(),q=D(10),c=D(".15"),
                     v=D(".55"),beta=D(".25"),ratio=D("1.25"),
                     scale=D(".15"))
        cases=[
            ("H0_EARLY_LIQUIDITY_5",replace(base,liquidity=D(5))),
            ("H0_CONTRACT_BETA_ZERO",replace(base,beta=D(0))),
            ("H0_HIGH_TRANSACTION_GAS",replace(base,gas=D(50)))
        ]
        records=[]
        for label,p in cases:
            engine=ContinuousDesigner(p,max_nodes=2400)
            cert=engine.solve()
            cert["robustness_name"]=label
            cert["reference"]=engine._serialize_row(engine.at(p.scale))
            cert["cash_cap"]=str(liquidity_bound(p))
            cert["beta_assumed"]=str(p.beta)
            cert["gas_assumed"]=str(p.gas)
            records.append(cert)
        return records


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="results/gate28")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    data=study()
    extra=robustness()
    (out/"CONTINUOUS_SCALE_CERTIFICATES_SYNTHETIC.json").write_text(json.dumps(data,indent=2)+"\n")
    (out/"REGIME_ROBUSTNESS_SYNTHETIC.json").write_text(json.dumps(extra,indent=2)+"\n")
    summary=[
        {k:row.get(k) for k in
         ("benchmark","q","status","best_feasible_scale_numeric",
          "smallest_feasible_scale_lower_bound_numeric","scale_gap_numeric",
          "modeled_output_at_feasible_scale","sampled_regimes","gate21_menu_selected")}
        for row in data
    ]
    (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
    print("REGIME_ROBUSTNESS="+json.dumps([
      dict(case=x["robustness_name"], status=x["status"],
           selected=x.get("selected_feasible"),
           at_historical_scale=x["reference"]["regime"])
      for x in extra],default=str))


if __name__=="__main__":
    main()
