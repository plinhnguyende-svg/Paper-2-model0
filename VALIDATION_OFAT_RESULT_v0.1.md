# One-Factor Sensitivity Result v0.1

## Run identity

- GitHub Actions run: 35334184221
- Branch: `verification-validation-v0.1`
- Head used by the validation run: `ac8f7037daec96ae398816041d3c7226f82e6485`
- Artifact: `validation-ofat_all-35334184221`
- Artifact SHA-256: `a62d307a8198a3cca890f0ed1ba5c1dd725233a94857c2ecaa70e91f0634f2e8`
- Paired replications per parameter value: 50
- Baseline warm-up: 200 days
- Contrasts: S-N and F-S

## Factors audited

1. symmetric exporter availability probability:
   [
   p\in\{0.50,0.60,0.70,0.80,0.90,1.00\};
   ]
2. shelf life:
   [
   L\in\{3,5,7,10,14\};
   ]
3. exporter-to-importer lead time:
   [
   \ell_{EB}\in\{1,2,3,4\};
   ]
4. importer-to-retailer lead time:
   [
   \ell_{BR}\in\{1,2,3\};
   ]
5. demand-forecast smoothing weight:
   [
   \alpha\in\{0.10,0.30,0.50,0.70,1.00\}.
   ]

The analysis uses the 11 protocol-defined primary outcomes and the two primary paired contrasts, giving 22 metric-contrast combinations per parameter value.

## Factor-level directional sensitivity

| Factor | Primary metric-contrast combinations whose CI-direction changes over the tested values |
|---|---:|
| exporter availability probability, including the theoretical boundary p=1 | 22 / 22 |
| exporter availability probability, excluding p=1 | 6 / 22 |
| shelf life | 12 / 22 |
| exporter-to-importer lead time | 8 / 22 |
| importer-to-retailer lead time | 6 / 22 |
| forecast smoothing weight | 2 / 22 |

## Availability boundary check

At
[
p=1,
]
all 22 primary paired effects are exactly zero in the generated experiment output:

[
S-N=0,\qquad F-S=0.
]

This reproduces the Model 0 perfect-availability neutrality property rather than creating a spurious robustness failure.

For (p<1), several operational outcomes keep a stable direction over the tested availability range. In particular:

- service level: (S-N<0) and (F-S>0);
- total lost sales: (S-N>0) and (F-S<0);
- total waste and waste share: (S-N>0) and (F-S<0);
- mean total inventory: (S-N>0) and (F-S<0).

However, some S-N allocation-gap and bullwhip effects change direction as reliability changes. Examples include:

- mean absolute stock-allocation gaps: S-N is negative at (p=0.5,0.6), then positive from (p=0.7);
- mean absolute target-allocation gaps: S-N is negative through (p=0.7), then positive from (p=0.8);
- importer-procurement bullwhip: S-N is negative through (p=0.8) and CI-overlaps-zero at (p=0.9).

## Perishability sensitivity

Shelf life generates the broadest non-boundary directional changes among the tested one-factor perturbations: 12 of 22 primary metric-contrast combinations change CI-direction somewhere over (L\in\{3,5,7,10,14\}).

Notable examples:

- importer-procurement bullwhip exhibits sign changes in both S-N and F-S at short shelf life;
- service-level and lost-sales contrasts move from CI-overlapping-zero or one sign at short shelf life to the opposite sign at longer shelf life for some comparisons;
- waste effects attenuate toward CI-overlapping-zero at long shelf life.

This is consistent with perishability being an economically active mechanism dimension rather than a passive background parameter.

## Lead-time sensitivity

Both lead-time dimensions generate systematic sign changes.

For exporter-to-importer lead time, 8 of 22 primary combinations change CI-direction. The affected outcomes include service level, lost sales, retail-order bullwhip, and importer-procurement bullwhip.

For importer-to-retailer lead time, 6 of 22 primary combinations change CI-direction. The strongest changes are concentrated in F-S service, lost sales, waste, and retail-order bullwhip.

These patterns indicate that the effect of information visibility can interact with physical delay rather than being separable from logistics timing.

## Forecast-policy sensitivity

The smoothing parameter is comparatively less disruptive: only 2 of 22 primary combinations change CI-direction over the tested range. Both are S-N bullwhip measures:

- importer-procurement bullwhip;
- retail-order bullwhip.

The remaining 20 primary metric-contrast combinations retain their CI-direction over the tested smoothing weights.

## Interpretation

The OFAT stage rejects two overly strong interpretations:

1. the baseline N/S/F pattern is **not** merely a numerical artifact of one exact baseline parameter vector, because many contrasts persist over substantial one-factor ranges and the perfect-availability neutrality boundary is recovered exactly;
2. the N/S/F ordering is **not universal**, because several outcomes exhibit systematic sign reversals as perishability, reliability, and lead times change.

The appropriate research interpretation is therefore a **conditional mechanism effect with parameter-dependent regions**, not a universal regime ranking.

A directional reversal over a structured parameter interval is treated as a substantive boundary result to be mapped, not as a failed validation test.

## Stage decision

[
\boxed{
\text{OFAT reveals structured parameter dependence; proceed to two-dimensional robustness phase maps.}
}
]

The pre-specified primary phase maps are:

[
p\times L
]

and

[
p\times \ell_{EB}.
]

They will be used to determine whether the OFAT sign changes form coherent regions or isolated points.
