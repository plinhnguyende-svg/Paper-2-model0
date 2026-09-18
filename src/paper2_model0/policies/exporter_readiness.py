from dataclasses import dataclass
from paper2_model0.domain.observations import ExporterObservation


@dataclass(frozen=True)
class ExporterReadinessAction:
    readiness_target: float
    prepared_quantity: float


class RuleBasedExporterReadinessPolicy:
    def decide(self, observation: ExporterObservation) -> ExporterReadinessAction:
        if not observation.own_operational_availability:
            return ExporterReadinessAction(0.0, 0.0)

        q = observation.announced_procurement_requirement
        if not observation.buyer_uses_verified_state_contingent_allocation:
            target = q / 2.0
        elif observation.rival_operational_availability is None:
            p = observation.rival_availability_probability
            target = (1.0 - p) * q + p * q / 2.0
        else:
            target = q if not observation.rival_operational_availability else q / 2.0

        prepared = max(0.0, target - observation.own_on_hand_inventory)
        return ExporterReadinessAction(target, prepared)
