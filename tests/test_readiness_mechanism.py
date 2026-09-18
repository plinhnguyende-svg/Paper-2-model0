from paper2_model0.architectures import build_architecture
from paper2_model0.policies.exporter_readiness import RuleBasedExporterReadinessPolicy


def test_deterministic_s_f_readiness_mechanism_q100_p05_rival_down():
    policy = RuleBasedExporterReadinessPolicy()
    availability = (True, False)

    s_obs = build_architecture("S").exporter_observation(
        day=0,
        exporter_index=0,
        procurement_requirement=100.0,
        on_hand_inventory=0.0,
        availability=availability,
        rival_availability_probability=0.5,
    )
    f_obs = build_architecture("F").exporter_observation(
        day=0,
        exporter_index=0,
        procurement_requirement=100.0,
        on_hand_inventory=0.0,
        availability=availability,
        rival_availability_probability=0.5,
    )
    s_action = policy.decide(s_obs)
    f_action = policy.decide(f_obs)
    assert s_action.readiness_target == 75.0
    assert s_action.prepared_quantity == 75.0
    assert f_action.readiness_target == 100.0
    assert f_action.prepared_quantity == 100.0
