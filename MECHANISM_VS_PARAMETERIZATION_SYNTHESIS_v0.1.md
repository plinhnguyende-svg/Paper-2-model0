# Mechanism vs. Parameterization Synthesis v0.1

## Research question

This synthesis answers the validation question for Model 0:

> Are the observed N/S/F contrasts properties of the information mechanism, or artifacts of initialization, finite simulation design, random seed, or a narrow parameterization?

The evidence does not support a binary answer in which every outcome is either universally structural or merely an artifact. Instead, Model 0 separates into:

1. direct information-mechanism effects that are highly stable over the tested region; and
2. downstream system outcomes whose sign depends systematically on perishability, reliability, and logistics delay.

This is a conditional-mechanism conclusion, not a universal ranking of N, S, and F.

## Evidence chain

### 1. Verification and treatment isolation

The existing verification suite establishes that N, S, and F share the same physical system and differ through the intended information architecture and its decision consequences.

The already-tested perfect-availability boundary implies:

[
p=1\Rightarrow N=S=F.
]

The phase maps reproduce this boundary exactly.

### 2. Warm-up convergence

Candidate warm-ups

[
W\in\{0,50,100,200,300,400\}
]

were evaluated with a fixed 600-day measurement window and 30 paired replications.

Across all 22 primary metric-contrast combinations, CI-direction did not change with the candidate warm-up. The baseline 200-day warm-up was therefore retained.

Interpretation: the baseline contrast pattern is not being created by the initial transient.

### 3. Replication sufficiency

Nested paired-replication checkpoints

[
n\in\{10,20,30,50,100,200\}
]

preserved the same CI-direction for all 22 primary combinations.

The (n=50) and (n=200) confidence intervals overlap for every primary combination.

Interpretation: the qualitative contrast pattern is not a small-replication artifact. Fifty paired replications are adequate as a working design for broad robustness experiments, while 200 remains the higher-precision baseline reference.

### 4. Seed stability

Five independent master seeds, each with 50 paired replications, preserved the CI-direction of all 22 primary combinations.

Interpretation: the baseline contrast pattern is not dependent on one arbitrary master random stream.

### 5. One-factor sensitivity

OFAT showed that the model is not insensitive to its primitives.

Directional changes occurred most often under:

- shelf life: 12/22 primary combinations;
- exporter-to-importer lead time: 8/22;
- importer-to-retailer lead time: 6/22;
- exporter reliability excluding (p=1): 6/22;
- forecast smoothing weight: 2/22.

Interpretation: some downstream findings are conditional, and this conditionality is strongest in perishability and physical-delay dimensions.

### 6. Two-dimensional phase maps

The pre-specified maps

[
p\times L
]

and

[
p\times\ell_{EB}
]

show that many OFAT sign changes form coherent regions rather than isolated points.

The most important distinction is between direct mechanism outcomes and system-level outcomes.

## Finding A: horizontal rival visibility has a stable direct readiness-alignment mechanism

Across all 45 interior phase-map cells with (p<1):

[
F-S<0
]

for all four readiness-alignment measures:

[
	ext{target-allocation gap}_{1},
quad
	ext{target-allocation gap}_{2},
]

[
	ext{stock-allocation gap}_{1},
quad
	ext{stock-allocation gap}_{2}.
]

Thus, within the tested Model 0 design:

[
oxed{
	ext{horizontal rival visibility consistently improves exporter readiness/allocation alignment.}
}
]

This result is also economically close to the information treatment itself: F gives exporters the rival's realized availability while S does not.

It is therefore the strongest candidate for a mechanism property in the current model.

## Finding B: horizontal visibility usually reduces inventory and waste, but downstream performance is conditional

For F-S over the 45 interior phase cells:

- mean total inventory: 44 negative, 1 CI-overlapping-zero;
- total waste: 39 negative, 6 CI-overlapping-zero;
- waste share: 33 negative, 11 CI-overlapping-zero, 1 positive;
- service level: 37 positive, 7 CI-overlapping-zero, 1 negative;
- total lost sales: 37 negative, 7 CI-overlapping-zero, 1 positive.

This is broad evidence of operational improvement over much of the tested region, but the single sign reversals and zero-transition regions prevent a universal dominance claim.

The exceptions are structured. For example, the adverse F-S service cell occurs at high availability and the longest tested upstream lead time:

[
p=0.9,qquad \ell_{EB}=4.
]

## Finding C: bullwhip effects are conditional mechanism outcomes, not universal effects

Importer-procurement bullwhip under F-S is negative in 41 of 45 interior cells, but positive when shelf life is extremely short and availability is low-to-moderate:

[
L=3,qquad p\in\{0.5,0.6,0.7\}.
]

Retail-order bullwhip under F-S is negative in 35 cells, CI-overlapping-zero in 8, and positive in 2. The positive cells occur at the longest upstream lead time with lower availability:

[
\ell_{EB}=4,qquad p\in\{0.5,0.6\}.
]

Therefore:

[
oxed{
	ext{visibility does not have a universal monotone bullwhip effect in Model 0.}
}
]

Its effect propagates through perishability, delay, inventory carry-over, and replenishment dynamics.

## Finding D: S-N vertical verification is more parameter-sensitive than the direct F-S readiness mechanism

The S-N contrast changes sign for service, lost sales, both bullwhip measures, and both target- and stock-allocation gaps over the tested phase regions.

At the same time, two broad S-N regularities persist:

[
S-N>0
]

for mean total inventory in all 45 interior cells, and total waste is positive in 40 cells with the remaining 5 CI-overlapping-zero.

This means that state-contingent importer allocation does not generate a single universally beneficial operational response in the present rule-based system. Its consequences depend strongly on how verification interacts with perishability and logistics timing.

## Overall answer to the reviewer question

The accumulated validation evidence rejects the proposition that the baseline N/S/F results are merely artifacts of:

- the 200-day warm-up;
- using only 50 replications;
- one master seed; or
- one exact baseline parameter vector.

However, it also rejects an interpretation in which all N/S/F outcome differences are universal properties of blockchain visibility.

The scientifically supported conclusion is:

[
oxed{
egin{aligned}
&	ext{Direct information-to-readiness effects can be structural within Model 0,}\
&	ext{while service, waste, inventory, and bullwhip effects are conditional on}\
&	ext{the operational parameter region.}
end{aligned}
}
]

More specifically:

- the F-S reduction in target- and stock-allocation gaps is stable across every tested interior phase cell and is the cleanest mechanism result;
- F-S inventory and total-waste effects are broadly stable over the tested region;
- service and bullwhip effects exhibit coherent phase boundaries;
- S-N is substantially more region-dependent for several operational outcomes;
- all contrasts collapse exactly to zero at the theoretical boundary (p=1).

## What can and cannot be claimed

### Supported within the tested Model 0 design

It is supported to state that rival-availability visibility has a robust direct effect on readiness alignment and that the downstream value of additional transparency depends on perishability, reliability, and logistics delay.

It is also supported to state that the simulated findings survive warm-up, replication-count, and seed diagnostics and are not confined to one baseline point.

### Not supported

The current validation does not support:

- a universal ranking (F>S>N) or any other universal ordering;
- a claim that blockchain transparency always reduces bullwhip;
- external empirical validity for real food-export supply chains;
- independent demand-variance robustness, because the current Poisson process has no separate variance primitive;
- any AI-related conclusion, because AI has not been added to Model 0.

## Research implication

The validated RuleBased model should therefore be carried forward as a conditional benchmark:

[
oxed{
{N,S,F}\times\{RuleBased\}
}
]

with explicit phase boundaries retained rather than averaged away.

Only after this validation branch is frozen should the AI decision architecture be introduced. The subsequent AI extension should be evaluated against the same information regimes and should preserve the validated exogenous-scenario and treatment-isolation design.

## Validation decision

[
oxed{
	ext{Model 0 passes mechanism verification, while external and AI validation remain future stages.}
}
]

"Pass" here means that the implemented mechanism behaves reproducibly and generates interpretable parameter-region structure under the pre-specified computational tests. It does not mean that every outcome is invariant to parameters or empirically validated outside the simulation.
