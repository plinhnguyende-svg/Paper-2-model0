from paper2_model0.domain.observations import ImporterObservation


class RuleBasedImporterAllocationPolicy:
    def decide(self, procurement_requirement: float, observation: ImporterObservation) -> tuple[float, float]:
        q = float(procurement_requirement)
        availability = observation.verified_exporter_availability
        if availability == (None, None):
            return q / 2.0, q / 2.0

        active = int(bool(availability[0])) + int(bool(availability[1]))
        if active == 0:
            return 0.0, 0.0
        return (
            q * int(bool(availability[0])) / active,
            q * int(bool(availability[1])) / active,
        )
