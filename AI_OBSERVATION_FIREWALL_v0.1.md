# AI Observation Firewall v0.1

## Purpose

This milestone creates the decision-policy boundary for the future
({N,S,F}\times{RuleBased,AI}) experiment.

It does **not** train an AI agent and does **not** compare performance.

The only scientific question at this stage is:

> Can a future AI decision architecture be substituted into the simulator
> without receiving information that the corresponding N, S, or F regime
> does not permit?

## Design

The engine now uses an `ObservationSafeDecisionArchitecture` container whose
actor policies are separate stateful objects.

The container provides:

1. three retailer policy instances, one per retailer;
2. one importer policy instance, covering importer replenishment and allocation;
3. two exporter policy instances, one per exporter.

The container itself receives no observations. The engine routes each frozen
typed observation directly to the policy instance belonging to the actor that
is permitted to observe it. Static configuration is bound when the actor policy
is constructed.

The validated RuleBased policies are retained behind
`RuleBasedDecisionArchitecture`, which creates actor-isolated adapters around
the original policy implementations.

## Information firewall

| Decision boundary | N | S | F |
|---|---|---|---|
| Retailer replenishment | retailer-local observation | same schema | same schema |
| Importer replenishment | no current exporter availability | same | same |
| Importer allocation | exporter availability hidden | verified current exporter availability | same verified importer information as S |
| Exporter readiness | own availability; rival current state hidden | own availability; rival current state hidden | own + rival current availability |

The future AI implementation must use exactly these policy-boundary
observations. It must not read the `SupplyChainModel`, `ExogenousScenario`,
raw demand path, or raw exporter-availability path.

Policy instances must also be actor-isolated. The same mutable policy object
cannot be reused for two retailers, two exporters, or across importer/exporter
roles. This prevents a trivial memory side channel in which one agent caches a
state observation and another agent later reads it.

## Why importer replenishment has a separate observation

The procurement requirement (Q_t) is formed before current exporter
availability is revealed. Therefore importer replenishment receives
`ImporterReplenishmentObservation`, which contains retailer orders, the
importer's forecast, on-hand inventory, and usable pipeline inventory, but no
current exporter availability.

This preserves the identification rule that N/S/F information changes
allocation and readiness behavior rather than directly changing the
pre-revelation procurement requirement through hidden simulator access.

## Tests

`tests/test_ai_information_firewall.py` verifies:

- observation schemas contain no raw model/scenario handles;
- importer replenishment cannot observe current exporter state;
- N hides current exporter availability from importer allocation;
- S and F expose the same verified current exporter state to the importer;
- N and S hide rival current availability from exporters;
- F exposes rival current availability to exporters;
- each retailer and exporter is routed to a distinct policy instance;
- shared actor-policy instances are rejected as an information side channel;
- a deterministic AI-shaped stub can replace the RuleBased decision
  architecture without changing outputs when it delegates the same decisions;
- no decision-boundary observation exposes the exogenous scenario object.

## Non-result statement

Passing these tests establishes treatment isolation at the software interface.
It is **not** evidence that AI improves any operational outcome.

Training, optimization, and performance comparisons remain out of scope until
this firewall milestone is reviewed and merged.
