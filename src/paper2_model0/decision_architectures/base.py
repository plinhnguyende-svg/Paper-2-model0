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


class ObservationSafeDecisionArchitecture(Protocol):
    """Decision interface that receives observations, never the simulation model.

    Static configuration may be bound when an implementation is constructed.
    Current-period physical state enters decisions only through the typed,
    immutable observation objects supplied by the engine.
    """

    name: str

    def retailer_replenishment(
        self, observation: RetailerObservation
    ) -> RetailerAction: ...

    def importer_replenishment(
        self, observation: ImporterReplenishmentObservation
    ) -> ImporterReplenishmentAction: ...

    def importer_allocation(
        self,
        procurement_requirement: float,
        observation: ImporterObservation,
    ) -> tuple[float, float]: ...

    def exporter_readiness(
        self, observation: ExporterObservation
    ) -> ExporterReadinessAction: ...
