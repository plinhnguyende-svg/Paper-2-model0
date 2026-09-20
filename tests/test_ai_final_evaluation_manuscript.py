from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_ai_final_evaluation_manuscript_v0.1.py"
SPEC = importlib.util.spec_from_file_location("r4_validate", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def test_r4_frozen_authorities_and_prose_contract():
    root = Path(__file__).resolve().parents[1]
    MOD.validate_frozen_authorities(root)
    MOD.validate_prose(
        root / "manuscript/AI_FINAL_EVALUATION_RESULTS_DISCUSSION_v0.1.md",
        root / "experiments/ai_final_evaluation_manuscript_claim_registry_v0.1.json",
    )


def test_r4_has_no_scientific_recomputation_imports():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "evaluation_analysis" not in source
    assert "paired_bootstrap" not in source
    assert "panel_arrays" not in source
    assert "panel.jsonl" not in source
