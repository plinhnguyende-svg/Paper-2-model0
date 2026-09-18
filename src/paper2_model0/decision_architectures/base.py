from __future__ import annotations

from typing import Protocol

from paper2_model0.domain.observations import (
    ExporterObservation,
    ImporterObservation,
    ImporterReplenishmentObservation,
    RetailerObservation,
)
from paper2_model0.policies.exporter_readiness import ExporterReadinessAction
from paper2_model0.policies.importer_replenishment import ImporterReplenishmentAction
from paper2_model0.policies.retailer_replenishment import RetailerAction


class RetailerDecisionPolicy(Protocol):
    def decide(self, observation: RetailerObservation) -> RetailerAction: ...


class ImporterDecisionPolicy(Protocol):
    def decide_replenishment(
        self, observation: ImporterReplenishmentObservation
    ) -> ImporterReplenishmentAction: ...

    def decide_allocation(
        self,
        procurement_requirement: float,
        observation: ImporterObservation,
    ) -> tuple[float, float]: ...


class ExporterDecisionPolicy(Protocol):
    def decide(self, observation: ExporterObservation) -> ExporterReadinessAction: ...


class ObservationSafeDecisionArchitecture(Protocol):
    """Container of actor-isolated policy instances.

    The container itself receives no observations. Current-period information is
    routed by the engine directly to the policy instance belonging to the actor
    that is allowed to observe it.
    """

    name: str
    retailer_policies: tuple[
        RetailerDecisionPolicy,
        RetailerDecisionPolicy,
        RetailerDecisionPolicy,
    ]
    importer_policy: ImporterDecisionPolicy
    exporter_policies: tuple[
        ExporterDecisionPolicy,
        ExporterDecisionPolicy,
    ]


def validate_decision_architecture(
    architecture: ObservationSafeDecisionArchitecture,
) -> None:
    """Reject policy bundles that can trivially share actor-local mutable state."""

    if len(architecture.retailer_policies) != 3:
        raise ValueError("Decision architecture must provide exactly 3 retailer policies.")
    if len(architecture.exporter_policies) != 2:
        raise ValueError("Decision architecture must provide exactly 2 exporter policies.")

    controllers = [
        *architecture.retailer_policies,
        architecture.importer_policy,
        *architecture.exporter_policies,
    ]
    identities = [id(controller) for controller in controllers]
    if len(set(identities)) != len(identities):
        raise ValueError(
            "Actor policy instances must be distinct; shared policy objects create "
            "an information side channel across agents."
        )
