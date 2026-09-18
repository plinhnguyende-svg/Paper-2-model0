from __future__ import annotations

import numpy as np
import pytest

from paper2_model0.ai import (
    AIObservationEncoder,
    BoundedActionTransformer,
    FixedForecastTransitionAdapter,
    stable_sigmoid,
)
from paper2_model0.config import SimulationConfig
from paper2_model0.domain.observations import (
    ExporterObservation,
    ImporterReplenishmentObservation,
    RetailerObservation,
)
from paper2_model0.policies.importer_replenishment import (
    RuleBasedImporterReplenishmentPolicy,
)
from paper2_model0.policies.retailer_replenishment import (
    RuleBasedRetailerReplenishmentPolicy,
)


def _config():
    return SimulationConfig(
        shelf_life_days=7,
        retailer_mean_demand=(10.0, 20.0, 30.0),
        demand_forecast_smoothing_weight=0.3,
    )


def _retailer_obs():
    return RetailerObservation(
        current_day=17,
        current_consumer_demand=15.0,
        on_hand_inventory=12.0,
        usable_pipeline_inventory=8.0,
        previous_forecast=10.0,
    )


def _importer_obs():
    return ImporterReplenishmentObservation(
        current_day=17,
        current_retailer_orders=(12.0, 18.0, 33.0),
        previous_forecast=60.0,
        on_hand_inventory=40.0,
        usable_pipeline_inventory=20.0,
    )


def _exporter_obs(*, rival, own=True, q=100.0, stock=25.0, buyer_verified=True):
    return ExporterObservation(
        current_day=17,
        announced_procurement_requirement=q,
        own_operational_availability=own,
        rival_operational_availability=rival,
        own_on_hand_inventory=stock,
        rival_availability_probability=0.8,
        buyer_uses_verified_state_contingent_allocation=buyer_verified,
    )


def test_encoder_dimensions_and_exact_normalization():
    encoder = AIObservationEncoder.from_config(_config())

    retailer = encoder.encode_retailer(_retailer_obs(), 0)
    importer = encoder.encode_importer_replenishment(_importer_obs())

    np.testing.assert_allclose(retailer, [1.5, 1.2, 0.8, 1.0])
    np.testing.assert_allclose(
        importer,
        [
            1.2,
            0.9,
            1.1,
            1.0,
            40.0 / 60.0,
            20.0 / 60.0,
        ],
    )
    assert retailer.shape == (4,)
    assert importer.shape == (6,)
    assert retailer.dtype == np.float64
    assert importer.dtype == np.float64


def test_encoder_excludes_day_and_regime_by_construction():
    encoder = AIObservationEncoder.from_config(_config())
    obs_a = _retailer_obs()
    obs_b = RetailerObservation(
        current_day=999,
        current_consumer_demand=obs_a.current_consumer_demand,
        on_hand_inventory=obs_a.on_hand_inventory,
        usable_pipeline_inventory=obs_a.usable_pipeline_inventory,
        previous_forecast=obs_a.previous_forecast,
    )

    np.testing.assert_array_equal(
        encoder.encode_retailer(obs_a, 0),
        encoder.encode_retailer(obs_b, 0),
    )


def test_exporter_encoder_uses_known_value_mask_without_dimension_change():
    encoder = AIObservationEncoder.from_config(_config())

    hidden = encoder.encode_exporter(_exporter_obs(rival=None))
    visible_down = encoder.encode_exporter(_exporter_obs(rival=False))
    visible_up = encoder.encode_exporter(_exporter_obs(rival=True))

    assert hidden.shape == visible_down.shape == visible_up.shape == (7,)

    # [Q/scale, own availability, own stock/scale, p_j, buyer verified, known, value]
    np.testing.assert_allclose(hidden, [100 / 60, 1, 25 / 60, 0.8, 1, 0, 0])
    np.testing.assert_allclose(
        visible_down, [100 / 60, 1, 25 / 60, 0.8, 1, 1, 0]
    )
    np.testing.assert_allclose(
        visible_up, [100 / 60, 1, 25 / 60, 0.8, 1, 1, 1]
    )


def test_encoder_rejects_nonpositive_ai_normalization_scale():
    config = SimulationConfig(retailer_mean_demand=(10.0, 0.0, 10.0))
    with pytest.raises(ValueError, match="strictly positive"):
        AIObservationEncoder.from_config(config)


def test_stable_sigmoid_is_bounded_and_numerically_stable():
    assert stable_sigmoid(0.0) == pytest.approx(0.5)
    assert stable_sigmoid(-1000.0) == pytest.approx(0.0)
    assert stable_sigmoid(1000.0) == pytest.approx(1.0)
    assert stable_sigmoid(float("-inf")) == pytest.approx(0.0)
    assert stable_sigmoid(float("inf")) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="NaN"):
        stable_sigmoid(float("nan"))


def test_fixed_forecast_transition_matches_frozen_rulebased_law():
    config = _config()
    adapter = FixedForecastTransitionAdapter(
        alpha=config.demand_forecast_smoothing_weight
    )

    retailer_obs = _retailer_obs()
    importer_obs = _importer_obs()

    rule_retailer = RuleBasedRetailerReplenishmentPolicy().decide(
        retailer_obs,
        alpha=config.demand_forecast_smoothing_weight,
        lead_time=config.importer_to_retailer_lead_time_days,
    )
    rule_importer = RuleBasedImporterReplenishmentPolicy().decide(
        retailer_orders=importer_obs.current_retailer_orders,
        previous_forecast=importer_obs.previous_forecast,
        on_hand_inventory=importer_obs.on_hand_inventory,
        usable_pipeline_inventory=importer_obs.usable_pipeline_inventory,
        alpha=config.demand_forecast_smoothing_weight,
        lead_time=config.exporter_to_importer_lead_time_days,
    )

    assert adapter.retailer_next_forecast(retailer_obs) == pytest.approx(
        rule_retailer.updated_forecast
    )
    assert adapter.importer_next_forecast(importer_obs) == pytest.approx(
        rule_importer.updated_forecast
    )


def test_retailer_target_is_bounded_by_shelf_life_times_mean_demand():
    config = _config()
    transformer = BoundedActionTransformer(
        shelf_life_days=config.shelf_life_days,
        retailer_mean_demand=config.retailer_mean_demand,
        forecast_transition=FixedForecastTransitionAdapter(
            config.demand_forecast_smoothing_weight
        ),
    )
    obs = _retailer_obs()

    low = transformer.retailer_action(-1000.0, obs, 0)
    mid = transformer.retailer_action(0.0, obs, 0)
    high = transformer.retailer_action(1000.0, obs, 0)

    max_target = config.shelf_life_days * config.retailer_mean_demand[0]
    inventory_position = obs.on_hand_inventory + obs.usable_pipeline_inventory

    assert low.replenishment_order == pytest.approx(0.0)
    assert mid.replenishment_order == pytest.approx(
        max(0.0, 0.5 * max_target - inventory_position)
    )
    assert high.replenishment_order == pytest.approx(
        max(0.0, max_target - inventory_position)
    )
    assert 0.0 <= high.replenishment_order <= max_target


def test_importer_procurement_target_is_bounded_and_pre_revelation():
    config = _config()
    transformer = BoundedActionTransformer(
        shelf_life_days=config.shelf_life_days,
        retailer_mean_demand=config.retailer_mean_demand,
        forecast_transition=FixedForecastTransitionAdapter(
            config.demand_forecast_smoothing_weight
        ),
    )
    obs = _importer_obs()

    action = transformer.importer_replenishment_action(1000.0, obs)
    max_target = config.shelf_life_days * sum(config.retailer_mean_demand)
    inventory_position = obs.on_hand_inventory + obs.usable_pipeline_inventory

    assert action.procurement_requirement == pytest.approx(
        max(0.0, max_target - inventory_position)
    )
    assert not hasattr(obs, "verified_exporter_availability")
    assert not hasattr(obs, "rival_operational_availability")


def test_exporter_readiness_is_forced_zero_when_unavailable():
    config = _config()
    transformer = BoundedActionTransformer(
        shelf_life_days=config.shelf_life_days,
        retailer_mean_demand=config.retailer_mean_demand,
        forecast_transition=FixedForecastTransitionAdapter(
            config.demand_forecast_smoothing_weight
        ),
    )

    action = transformer.exporter_readiness_action(
        1000.0,
        _exporter_obs(rival=False, own=False, q=100.0, stock=0.0),
    )
    assert action.readiness_target == 0.0
    assert action.prepared_quantity == 0.0


def test_exporter_readiness_target_is_bounded_by_current_procurement_requirement():
    config = _config()
    transformer = BoundedActionTransformer(
        shelf_life_days=config.shelf_life_days,
        retailer_mean_demand=config.retailer_mean_demand,
        forecast_transition=FixedForecastTransitionAdapter(
            config.demand_forecast_smoothing_weight
        ),
    )

    q = 100.0
    stock = 25.0
    low = transformer.exporter_readiness_action(
        -1000.0, _exporter_obs(rival=None, q=q, stock=stock)
    )
    mid = transformer.exporter_readiness_action(
        0.0, _exporter_obs(rival=None, q=q, stock=stock)
    )
    high = transformer.exporter_readiness_action(
        1000.0, _exporter_obs(rival=None, q=q, stock=stock)
    )

    assert 0.0 <= low.readiness_target <= q
    assert mid.readiness_target == pytest.approx(50.0)
    assert high.readiness_target == pytest.approx(q)
    assert high.prepared_quantity == pytest.approx(q - stock)
    assert low.prepared_quantity >= 0.0


def test_transformer_does_not_implement_importer_allocation():
    config = _config()
    transformer = BoundedActionTransformer(
        shelf_life_days=config.shelf_life_days,
        retailer_mean_demand=config.retailer_mean_demand,
        forecast_transition=FixedForecastTransitionAdapter(
            config.demand_forecast_smoothing_weight
        ),
    )
    assert not hasattr(transformer, "importer_allocation_action")
    assert not hasattr(transformer, "allocation_logits")
