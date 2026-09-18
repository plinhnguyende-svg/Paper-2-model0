# AI Extension Baseline Lock v0.1

## Frozen RuleBased benchmark

The AI extension starts from the validated RuleBased Model 0 merge commit:

`
4d9bb3058e34269231aa792070a600d00442a9f4
`

This commit contains the merged Model 0 Verification & Validation Protocol v0.1.

## Experimental design to preserve

The next model family is:

[
{N,S,F}	imes{RuleBased,AI}.
]

The validated RuleBased benchmark is not to be altered silently.

### Information regimes

- **N**: importer does not observe verified current exporter availability; exporters do not observe rival current availability.
- **S**: importer observes verified current exporter availability; exporters do not observe rival current availability.
- **F**: importer observes the same verified exporter availability as S; each exporter additionally observes rival current availability.

### Identification rule

AI changes the **decision architecture**, not the information architecture.

For every information regime, RuleBased and AI treatments must receive the same admissible observation set for that regime.

Any AI policy must therefore satisfy:

[
mathcal I_N^{AI}=mathcal I_N^{RuleBased},quad
mathcal I_S^{AI}=mathcal I_S^{RuleBased},quad
mathcal I_F^{AI}=mathcal I_F^{RuleBased}.
]

The AI extension must not obtain hidden physical state merely because the simulator has access to it.

## Exogenous-scenario rule

RuleBased and AI treatments must use common exogenous scenarios within each paired replication wherever the comparison requires treatment isolation.

## Scope rule

Do not change the validated physical network, perishability mechanics, FEFO logic, demand process, or N/S/F information rights in the first AI implementation.

Any later extension that changes those elements must be separated from the AI decision-architecture treatment.

## First implementation target

The first AI milestone is an **observation-safe policy interface** and deterministic test harness. It should prove that an AI policy can be substituted for a RuleBased policy without receiving any information that the corresponding regime does not permit.

No performance claim should be made before those information-firewall tests pass.
