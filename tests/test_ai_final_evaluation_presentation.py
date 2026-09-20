from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_ai_final_evaluation_manuscript_v0.1.py"
SPEC = importlib.util.spec_from_file_location("r3_render", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def test_r3_pins_exact_frozen_registry_blobs_and_scopes():
    assert MOD.PRIMARY_BLOB == "40d590f742c85f7e853bd3766a41fc335510b4b9"
    assert MOD.SECONDARY_BLOB == "3f99a7cca25e4ee7248d48e90d1db5aa45a08fe1"
    assert len(MOD.PRIMARY_ORDER) == 5
    assert len(MOD.SECONDARY_ORDER) == 4
    assert set(MOD.PRIMARY_ORDER).isdisjoint(MOD.SECONDARY_ORDER)


def test_r3_renderer_has_no_raw_panel_or_estimator_import_path():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "panel.jsonl" not in source
    assert "evaluation_analysis" not in source
    assert "paired_bootstrap" not in source
    assert "panel_arrays" not in source


def test_r3_generates_separate_primary_and_exploratory_outputs(tmp_path):
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "presentation"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--primary-registry",
            str(root / "experiments/ai_final_evaluation_result_registry_v0.1.json"),
            "--secondary-registry",
            str(root / "experiments/ai_final_evaluation_secondary_result_registry_v0.1.json"),
            "--output-dir",
            str(out),
        ],
        check=True,
        cwd=root,
    )
    expected = {
        "table_primary_interactions.csv",
        "table_primary_interactions.md",
        "figure_primary_interactions.svg",
        "table_exploratory_interactions.csv",
        "table_exploratory_interactions.md",
        "figure_exploratory_interactions.svg",
    }
    assert {p.name for p in out.iterdir()} == expected
    assert "PRIMARY" in (out / "table_primary_interactions.md").read_text()
    assert "EXPLORATORY" in (out / "table_exploratory_interactions.md").read_text()
    assert "PRIMARY" in (out / "figure_primary_interactions.svg").read_text()
    assert "EXPLORATORY" in (out / "figure_exploratory_interactions.svg").read_text()


def test_committed_r3_outputs_are_exact_renderer_outputs(tmp_path):
    root = Path(__file__).resolve().parents[1]
    generated = tmp_path / "generated"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--primary-registry",
            str(root / "experiments/ai_final_evaluation_result_registry_v0.1.json"),
            "--secondary-registry",
            str(root / "experiments/ai_final_evaluation_secondary_result_registry_v0.1.json"),
            "--output-dir",
            str(generated),
        ],
        check=True,
        cwd=root,
    )
    committed = root / "outputs" / "manuscript_v0.1"
    for produced in sorted(generated.iterdir()):
        expected = committed / produced.name
        assert expected.is_file(), produced.name
        assert produced.read_bytes() == expected.read_bytes(), produced.name
