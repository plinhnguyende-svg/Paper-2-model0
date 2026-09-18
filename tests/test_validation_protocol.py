import numpy as np
import pandas as pd

from paper2_model0.config import SimulationConfig
from paper2_model0.validation import (
    apply_parameter,
    classify_ci_direction,
    ofat_diagnostic,
    phase_map_diagnostic,
    replication_sufficiency_diagnostic,
    seed_stability_diagnostic,
    summarize_paired_effects,
    summarize_phase_regions,
    warmup_convergence_diagnostic,
)


def tiny_config():
    return SimulationConfig(
        simulation_horizon_days=12,
        warmup_days=2,
        shelf_life_days=5,
        exporter_to_importer_lead_time_days=1,
        importer_to_retailer_lead_time_days=1,
        retailer_mean_demand=(3.0, 3.0, 3.0),
        demand_forecast_smoothing_weight=0.3,
        exporter_availability_probability=(0.8, 0.8),
    )


def test_classify_ci_direction():
    assert classify_ci_direction(0.1, 0.2) == "positive"
    assert classify_ci_direction(-0.2, -0.1) == "negative"
    assert classify_ci_direction(-0.1, 0.2) == "overlaps_zero"
    assert classify_ci_direction(float("nan"), 0.2) == "insufficient"


def test_apply_parameter_symmetric_availability_and_reject_unknown():
    config = apply_parameter(
        tiny_config(), "exporter_availability_probability_symmetric", 0.6
    )
    assert config.exporter_availability_probability == (0.6, 0.6)

    try:
        apply_parameter(config, "independent_demand_variance", 2.0)
    except ValueError as exc:
        assert "silently extended" in str(exc)
    else:
        raise AssertionError("unknown validation factor should be rejected")


def test_summarize_paired_effects_uses_replication_level_values():
    paired = pd.DataFrame(
        {
            "metric": ["m", "m", "m"],
            "S_minus_N": [1.0, 2.0, 3.0],
            "F_minus_S": [-1.0, -2.0, -3.0],
        }
    )
    out = summarize_paired_effects(paired)
    s = out[(out["metric"] == "m") & (out["effect"] == "S_minus_N")].iloc[0]
    assert s["n"] == 3
    assert np.isclose(s["mean"], 2.0)


def test_warmup_diagnostic_uses_fixed_measurement_window():
    out = warmup_convergence_diagnostic(
        tiny_config(),
        warmup_candidates_days=[0, 2],
        measurement_window_days=6,
        number_of_replications=2,
        master_seed=123,
    )
    assert set(out["warmup_days"]) == {0, 2}
    assert set(out["measurement_window_days"]) == {6}
    assert {"S_minus_N", "F_minus_S"}.issubset(set(out["effect"]))


def test_replication_sufficiency_is_nested():
    out = replication_sufficiency_diagnostic(
        tiny_config(),
        max_replications=4,
        checkpoints=[2, 4],
        master_seed=456,
    )
    assert set(out["replications"]) == {2, 4}
    assert (out["n"].isin([2, 4])).all()


def test_seed_stability_records_each_master_seed():
    out = seed_stability_diagnostic(
        tiny_config(),
        master_seeds=[11, 22],
        number_of_replications=2,
    )
    assert set(out["master_seed"]) == {11, 22}


def test_ofat_and_phase_map_preserve_declared_factors():
    ofat = ofat_diagnostic(
        tiny_config(),
        factor_name="shelf_life_days",
        values=[4, 5],
        number_of_replications=2,
        master_seed=77,
    )
    assert set(ofat["value"]) == {4, 5}

    phase = phase_map_diagnostic(
        tiny_config(),
        x_name="exporter_availability_probability_symmetric",
        x_values=[0.7, 0.8],
        y_name="shelf_life_days",
        y_values=[4, 5],
        number_of_replications=2,
        master_seed=88,
    )
    cells = phase[["x_value", "y_value"]].drop_duplicates()
    assert len(cells) == 4



def test_summarize_phase_regions_detects_sign_reversal_and_zero_region():
    phase = pd.DataFrame(
        {
            "map_index": [0, 0, 0, 0],
            "x_name": ["p"] * 4,
            "x_value": [0.5, 0.5, 0.8, 0.8],
            "y_name": ["L"] * 4,
            "y_value": [3, 7, 3, 7],
            "metric": ["service_level"] * 4,
            "effect": ["S_minus_N"] * 4,
            "direction": ["negative", "negative", "overlaps_zero", "positive"],
        }
    )
    out = summarize_phase_regions(phase)
    row = out.iloc[0]
    assert row["cells_total"] == 4
    assert row["cells_negative"] == 2
    assert row["cells_positive"] == 1
    assert row["cells_overlaps_zero"] == 1
    assert bool(row["has_sign_reversal"])
    assert bool(row["has_zero_boundary_region"])
