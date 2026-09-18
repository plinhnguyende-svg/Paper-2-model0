from paper2_model0.architectures import build_architecture


def make_obs(regime):
    a = build_architecture(regime)
    imp = a.importer_observation(
        day=0,
        retailer_orders=(1.0, 2.0, 3.0),
        on_hand_inventory=10.0,
        usable_pipeline_inventory=5.0,
        availability=(True, False),
    )
    e1 = a.exporter_observation(
        day=0,
        exporter_index=0,
        procurement_requirement=100.0,
        on_hand_inventory=0.0,
        availability=(True, False),
        rival_availability_probability=0.5,
    )
    return imp, e1


def test_information_sets_are_locked():
    imp_n, e_n = make_obs("N")
    imp_s, e_s = make_obs("S")
    imp_f, e_f = make_obs("F")

    assert imp_n.verified_exporter_availability == (None, None)
    assert imp_s.verified_exporter_availability == (True, False)
    assert imp_f.verified_exporter_availability == (True, False)

    assert e_n.rival_operational_availability is None
    assert e_s.rival_operational_availability is None
    assert e_f.rival_operational_availability is False

    assert e_n.buyer_uses_verified_state_contingent_allocation is False
    assert e_s.buyer_uses_verified_state_contingent_allocation is True
    assert e_f.buyer_uses_verified_state_contingent_allocation is True
