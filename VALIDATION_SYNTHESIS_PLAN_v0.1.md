# Mechanism-vs-Parameterization Synthesis Plan v0.1

## Purpose

This synthesis is written only after the pre-specified phase maps complete. It is designed to answer:

> Are the observed N/S/F contrasts stable implications of the information mechanism, or artifacts of a narrow parameterization?

It does **not** select a universally best regime.

## Evidence hierarchy

The synthesis uses six ordered checks:

1. verification / neutrality and treatment-isolation tests;
2. warm-up stability;
3. replication-count stability;
4. master-seed stability;
5. one-factor sensitivity;
6. two-dimensional phase-map structure.

A contrast is described as more structurally robust when its CI-direction is stable through checks 1-4 and occupies a non-trivial connected-looking region of the phase maps.

A contrast is described as parameter-dependent when the phase maps contain distinct positive and negative regions, especially when separated by CI-overlapping-zero cells.

A theoretical boundary such as perfect availability, where N=S=F by construction, is not counted as evidence against the mechanism.

## Phase-map interpretation rules

For each metric and each primary contrast (S-N and F-S), report:

- number/share of positive cells;
- number/share of negative cells;
- number/share of CI-overlapping-zero cells;
- whether both positive and negative cells occur;
- whether zero/uncertain cells form a transition region;
- whether any reversal is concentrated only at a theoretical boundary or extends into interior parameter values.

The automated helper `summarize_phase_regions` produces the cell counts and reversal flags. Economic interpretation of boundaries remains a substantive research step and must not be inferred solely from counts.

## Pre-specified maps

1. exporter reliability × shelf life:
   [
   p\times L
   ]

2. exporter reliability × exporter-to-importer lead time:
   [
   p\times \ell_{EB}
   ]

These maps were selected because OFAT showed the strongest non-boundary sensitivity in reliability, perishability, and upstream lead time.

## Final synthesis categories

Each primary metric-contrast relationship will be described using one of the following non-ranking categories:

- **stable over tested region**: one non-zero CI-direction dominates interior cells and no opposite sign appears;
- **boundary-sensitive**: effect collapses or changes only at a theoretical/degenerate boundary;
- **parameter-region dependent**: both positive and negative interior regions occur;
- **weak/uncertain over tested region**: CI-overlapping-zero cells dominate;
- **mixed evidence**: no single description is adequate.

These labels describe empirical-computational behavior of the simulated mechanism and are not claims of universal validity outside the tested Model 0 design.

## No-p-hacking rule

No new phase-map dimensions, value grids, outcomes, or seeds will be added merely because a desired sign is absent. Any post-hoc extension must be labeled exploratory and separated from this pre-specified validation protocol.
