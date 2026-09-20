"""Synthetic interruption/recovery exercise only; no held-out scenario access."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from paper2_model0.ai import evaluation as ev
from paper2_model0.ai import evaluation_execution as ex
from paper2_model0.ai.training_protocol import INFORMATION_REGIMES, TRAINING_SEEDS


def _rows(index: int, source: str) -> list[dict]:
    rows = []
    for regime in INFORMATION_REGIMES:
        for training_seed in (None, *TRAINING_SEEDS):
            rows.append({
                "scenario_index": index,
                "scenario_id": f"synthetic-execution-{index}",
                "evaluation_scenario_seed": str(ev.evaluation_seed_schedule()[index]),
                "regime": regime,
                "decision_architecture": "RuleBased" if training_seed is None else "AI",
                "training_seed": training_seed,
                "checkpoint_sha256": (
                    None if training_seed is None else next(
                        entry["final_checkpoint_sha256"]
                        for entry in ev.frozen_registry()["entries"]
                        if entry["regime"] == regime
                        and entry["training_seed"] == training_seed
                    )
                ),
                "source_sha": source,
                "registry_sha256": ev.REGISTRY_SHA256,
                **{metric: float(index + 1) for metric in ev.PRIMARY + ev.SECONDARY},
            })
    return rows


def main() -> dict:
    source = "a" * 40
    workflow = "b" * 40
    shard = ex.evaluation_shards()[0]
    contract = ex.build_execution_contract(
        shard=shard,
        source_commit_sha=source,
        workflow_commit_sha=workflow,
        origin_run_id=1,
    )
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "shard-000"
        store = ex.EvaluationShardStore(root, shard)
        store.initialize(contract)
        store.commit_scenario(_rows(0, source), contract)
        restored, _ = store.load(contract)
        ambiguous = store.scenario_path(1)
        ambiguous.write_bytes(b"partial")
        fail_closed = False
        try:
            store.load(contract)
        except RuntimeError:
            fail_closed = True
        return {
            "status": "SYNTHETIC_ONLY_NOT_SCIENTIFIC_RESULTS",
            "static_shards": ex.SHARD_COUNT,
            "scenarios_per_shard": ex.SCENARIOS_PER_SHARD,
            "total_trajectories": ex.TOTAL_TRAJECTORIES,
            "restored_committed_scenarios": restored,
            "ambiguous_resume_failed_closed": fail_closed,
            "heldout_scenarios_generated": 0,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()
    print(json.dumps(main(), sort_keys=True, allow_nan=False))
