# Validation Phase Map Result v0.1

## Run identity

- GitHub Actions run: `35338958125`
- Branch: `verification-validation-v0.1`
- Experiment head SHA: `b47b0d3a661b2013a8e1a9d8b53e5562cc33022d`
- Artifact: `validation-phase_all-35338958125`
- Artifact SHA-256: `08fae2e925c43f3d2315581b815e36e0256e1703e4de687d0b17488dd245bdef`
- Output file: `phase_maps_all.csv`
- Paired replications per phase-map cell: 30
- Baseline warm-up: 200 days
- Primary contrasts: `S-N` and `F-S`

The phase-map experiment completed successfully before the post-processing synthesis code was added. Therefore the reported phase-map cells come from the pre-specified grids and are not changed by the later interpretation helper.

## Pre-specified maps

### Map 0: exporter reliability × shelf life

[
p\in\{0.50,0.60,0.70,0.80,0.90,1.00\}
]

and

[
L\in\{3,5,7,10,14\}.
]

This gives 30 cells per metric/contrast.

### Map 1: exporter reliability × exporter-to-importer lead time

[
p\in\{0.50,0.60,0.70,0.80,0.90,1.00\}
]

and

[
\ell_{EB}\in\{1,2,3,4\}.
]

This gives 24 cells per metric/contrast.

Across the 11 protocol-defined primary outcomes and the two primary contrasts, the analysis contains 1,188 primary metric-contrast-cell observations.

## Theoretical boundary check

At the perfect-availability boundary

[
p=1,
]

all 198 primary phase-map observations at that boundary have exactly zero paired mean:

[
S-N=0,\qquad F-S=0.
]

All are classified as CI-overlapping-zero. This exactly reproduces the previously verified perfect-availability neutrality property:

[
oxed{p=1\Rightarrow N=S=F.}
]

The (p=1) boundary is therefore excluded when assessing whether opposite signs occur in the interior tested region.

## Interior-region counts

The table below aggregates the two phase maps over the 45 interior cells with (p<1).

| Outcome | Contrast | Positive cells | Negative cells | CI-overlaps-zero | Interior interpretation |
|---|---|---:|---:|---:|---|
| service level | S-N | 14 | 26 | 5 | parameter-region dependent |
| service level | F-S | 37 | 1 | 7 | mostly positive, but parameter-region dependent |
| waste share of terminal outflow | S-N | 35 | 0 | 10 | stable positive / attenuating toward zero |
| waste share of terminal outflow | F-S | 1 | 33 | 11 | mostly negative, one interior reversal |
| retail-order bullwhip | S-N | 23 | 15 | 7 | parameter-region dependent |
| retail-order bullwhip | F-S | 2 | 35 | 8 | mostly negative, but parameter-region dependent |
| importer-procurement bullwhip | S-N | 16 | 27 | 2 | parameter-region dependent |
| importer-procurement bullwhip | F-S | 3 | 41 | 1 | mostly negative, but parameter-region dependent |
| target-allocation gap 1 | S-N | 18 | 26 | 1 | parameter-region dependent |
| target-allocation gap 1 | F-S | 0 | 45 | 0 | stable negative |
| target-allocation gap 2 | S-N | 19 | 23 | 3 | parameter-region dependent |
| target-allocation gap 2 | F-S | 0 | 45 | 0 | stable negative |
| stock-allocation gap 1 | S-N | 29 | 15 | 1 | parameter-region dependent |
| stock-allocation gap 1 | F-S | 0 | 45 | 0 | stable negative |
| stock-allocation gap 2 | S-N | 29 | 14 | 2 | parameter-region dependent |
| stock-allocation gap 2 | F-S | 0 | 45 | 0 | stable negative |
| total lost sales | S-N | 26 | 14 | 5 | parameter-region dependent |
| total lost sales | F-S | 1 | 37 | 7 | mostly negative, but parameter-region dependent |
| total waste | S-N | 40 | 0 | 5 | stable positive / attenuating toward zero |
| total waste | F-S | 0 | 39 | 6 | stable negative / attenuating toward zero |
| mean total inventory | S-N | 45 | 0 | 0 | stable positive |
| mean total inventory | F-S | 0 | 44 | 1 | stable negative / one uncertain cell |

## Coherent phase structures

The sign changes are not distributed like isolated random points. Several form interpretable regions.

### 1. Shelf life creates a clear service-level phase boundary for S-N

For every (p<1):

- at (L=5) and (L=7), (S-N<0);
- at (L=10) and (L=14), (S-N>0);
- at (L=3), the CI overlaps zero.

Thus the vertical-verification service effect changes sign primarily with perishability rather than with one arbitrary reliability value.

For F-S, service is positive for all (p<1) at (L\ge5), while (L=3) is CI-overlapping-zero.

### 2. Upstream lead time creates a second service boundary

For S-N:

- at (ell_{EB}=1), the effect is positive for (p=0.5,0.6,0.7,0.8) and negative at (p=0.9);
- at (ell_{EB}\ge2), the effect is negative throughout the tested interior.

For F-S:

- the effect is positive for all tested (p<1) at (ell_{EB}=1,2,3);
- at (ell_{EB}=4), it weakens to CI-overlapping-zero for (p=0.7,0.8) and becomes negative at (p=0.9).

The single negative F-S service cell is therefore located at high reliability plus the longest tested upstream lead time, not randomly across the grid.

### 3. Horizontal visibility has a robust direct mechanism effect on readiness alignment

For all 45 interior cells in both maps:

[
F-S<0
]

for each of the four readiness-alignment outcomes:

[
	ext{mean absolute target-allocation gap}_{1,2},
]

and

[
	ext{mean absolute stock-allocation gap}_{1,2}.
]

This is the strongest phase-map evidence for a structural F-S mechanism property inside Model 0: revealing rival availability to exporters consistently improves readiness/allocation alignment over the entire tested interior region.

### 4. Inventory and waste exhibit broad directional regularities

For all 45 interior cells:

[
S-N>0
]

for mean total inventory.

For F-S, mean total inventory is negative in 44 of 45 interior cells and CI-overlapping-zero in the remaining cell.

Total waste is positive for S-N in 40 cells and zero/uncertain in 5, with no negative interior cell. For F-S it is negative in 39 cells and zero/uncertain in 6, with no positive interior cell.

These results indicate broad directional regularity, although they should still be described as tested-region results rather than universal theorems.

### 5. Bullwhip effects are genuinely region-dependent

For importer-procurement bullwhip, F-S is negative in 41 of 45 interior cells but becomes positive at:

[
(L,p)=(3,0.5),(3,0.6),(3,0.7).
]

At (L=3,p=0.8) the CI overlaps zero, and at (L=3,p=0.9) it becomes negative. For every tested upstream lead time in Map 1, F-S importer-procurement bullwhip remains negative.

For retail-order bullwhip, F-S is mostly negative but becomes positive at the longest tested upstream lead time:

[
(ell_{EB},p)=(4,0.5),(4,0.6),
]

with a zero/uncertain transition at (p=0.7,0.8) and a negative effect at (p=0.9).

These are coherent boundary patterns, not evidence of a universal bullwhip ordering.

## Phase-map conclusion

The phase maps reject both extreme interpretations.

They do not support the claim that the baseline findings are isolated artifacts of one parameter vector. Several effects occupy large coherent regions and some direct mechanism outcomes retain the same direction over every tested interior cell.

They also do not support a universal claim that one information regime dominates for every operational outcome. Service and bullwhip effects can reverse as perishability and logistics delay change.

[
oxed{
	ext{Phase-map evidence supports structural direct mechanisms plus conditional system-level effects.}
}
]

The next step is to integrate this result with warm-up, replication-count, seed, and OFAT evidence in the final mechanism-versus-parameterization synthesis.
