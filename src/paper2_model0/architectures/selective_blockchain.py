from paper2_model0.domain.observations import ImporterObservation, ExporterObservation


class SelectiveBlockchainArchitecture:
    name = "S"

    def importer_observation(self, *, day, retailer_orders, on_hand_inventory,
                             usable_pipeline_inventory, availability):
        return ImporterObservation(
            current_day=day,
            current_retailer_orders=retailer_orders,
            on_hand_inventory=on_hand_inventory,
            usable_pipeline_inventory=usable_pipeline_inventory,
            verified_exporter_availability=(bool(availability[0]), bool(availability[1])),
        )

    def exporter_observation(self, *, day, exporter_index, procurement_requirement,
                             on_hand_inventory, availability,
                             rival_availability_probability):
        return ExporterObservation(
            current_day=day,
            announced_procurement_requirement=procurement_requirement,
            own_operational_availability=bool(availability[exporter_index]),
            rival_operational_availability=None,
            own_on_hand_inventory=on_hand_inventory,
            rival_availability_probability=rival_availability_probability,
            buyer_uses_verified_state_contingent_allocation=True,
        )
