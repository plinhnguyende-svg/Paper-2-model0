from __future__ import annotations

import json
from pathlib import Path


REGISTRY = Path("experiments/ai_training_checkpoint_registry_v0.1.json")


def _load():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_checkpoint_registry_is_exact_confirmatory_set():
    registry = _load()
    assert registry["workflow_run_id"] == 35439893662
    assert registry["workflow_execution_sha"] == (
        "0b455dd3e03c0597ec806f8aac73db0172f02262"
    )
    assert registry["frozen_launcher_source_sha"] == (
        "fb4f386703294990917e9d99e10013925a9a54d6"
    )
    assert registry["posthoc_budget_extension_allowed"] is False

    entries = registry["entries"]
    expected = [
        (regime, seed)
        for regime in ("N", "S", "F")
        for seed in (41001, 41002, 41003, 41004, 41005)
    ]
    actual = sorted(
        (entry["regime"], int(entry["training_seed"]))
        for entry in entries
    )
    assert actual == sorted(expected)
    assert len(entries) == 15
    assert len({entry["artifact_id"] for entry in entries}) == 15
    assert len({entry["final_checkpoint_sha256"] for entry in entries}) == 15


def test_checkpoint_registry_records_stability_without_seed_selection():
    registry = _load()
    entries = registry["entries"]

    stable = [
        (entry["regime"], int(entry["training_seed"]))
        for entry in entries
        if entry["training_stable"]
    ]
    assert stable == [("N", 41003)]
    assert registry["stable_run_count"] == 1
    assert registry["not_stabilized_run_count"] == 14

    for entry in entries:
        assert len(entry["artifact_digest"].removeprefix("sha256:")) == 64
        assert len(entry["final_checkpoint_sha256"]) == 64
        assert len(entry["final_manifest_sha256"]) == 64
        assert entry["final_checkpoint_file"] == "checkpoint_episode_1000.pt"
