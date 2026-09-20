from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "summarize_ai_final_evaluation_secondary.py"
SPEC = importlib.util.spec_from_file_location("r2_summary", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def test_r2_scope_is_exactly_four_registered_secondary_metrics():
    assert MOD.SECONDARY == (
        "retail_order_bullwhip",
        "total_lost_sales",
        "total_waste",
        "mean_abs_stock_allocation_gap_exporter_average",
    )
    assert "service_level" not in MOD.SECONDARY
    assert "mean_abs_target_allocation_gap_exporter_average" not in MOD.SECONDARY


def test_r2_pins_upstream_freezes_and_preheldout_estimator_blob():
    assert MOD.EXPECTED_RESULT_FREEZE_SHA == "7ea4ff9099525d1ee221905380f665f6d7627ff3"
    assert MOD.EXPECTED_INTERPRETATION_FREEZE_SHA == "ece7fd704e0e3151e3a5ef02bf660a9d5e343c8b"
    assert MOD.EXPECTED_ANALYSIS_BLOB_SHA == "d85cc1b9f673d0ecd801f9eb12142e9e861aecc2"
    assert MOD.EXPECTED_PANEL_SHA256 == "6ed8bbd779bf25f6f7370ee2e27439ce18915be98a9169d10dd1f08f6cf8c00c"
