from __future__ import annotations

import json
from pathlib import Path

import pytest

from paper2_model0.ai import evaluation as ev
from paper2_model0.ai import evaluation_execution as ex
from paper2_model0.ai.training_protocol import INFORMATION_REGIMES, TRAINING_SEEDS


SOURCE = "a" * 40
WORKFLOW = "b" * 40
RUN_ID = 123456


def contract(shard=None):
    return ex.build_execution_contract(
        shard=shard or ex.evaluation_shards()[0],
        source_commit_sha=SOURCE,
        workflow_commit_sha=WORKFLOW,
        origin_run_id=RUN_ID,
    )


def rows_for(index, c):
    seed = str(ev.evaluation_seed_schedule()[index])
    rows = []
    for regime in INFORMATION_REGIMES:
        rows.append({
            "scenario_index": index,
            "scenario_id": f"synthetic-{index}",
            "evaluation_scenario_seed": seed,
            "regime": regime,
            "decision_architecture": "RuleBased",
            "training_seed": None,
            "checkpoint_sha256": None,
            "source_sha": SOURCE,
            "registry_sha256": ev.REGISTRY_SHA256,
            **{m: 1.0 + index for m in ev.PRIMARY + ev.SECONDARY},
        })
        for training_seed in TRAINING_SEEDS:
            rows.append({
                "scenario_index": index,
                "scenario_id": f"synthetic-{index}",
                "evaluation_scenario_seed": seed,
                "regime": regime,
                "decision_architecture": "AI",
                "training_seed": training_seed,
                "checkpoint_sha256": next(
                    e["final_checkpoint_sha256"] for e in ev.frozen_registry()["entries"]
                    if e["regime"] == regime and e["training_seed"] == training_seed
                ),
                "source_sha": SOURCE,
                "registry_sha256": ev.REGISTRY_SHA256,
                **{m: 2.0 + index for m in ev.PRIMARY + ev.SECONDARY},
            })
    assert len(rows) == 18
    return rows


def test_static_matrix_is_exact_and_hashed():
    shards = ex.evaluation_shards()
    assert len(shards) == 40
    assert [i for s in shards for i in s.scenario_indices] == list(range(200))
    assert ex.TOTAL_TRAJECTORIES == 3600
    assert len(ex.shard_registry_sha256()) == 64
    assert len(ex.evaluation_schedule_sha256()) == 64


def test_candidate_shard_entrypoint_remains_closed_before_output(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("protected resource touched before freeze gate")
    monkeypatch.setattr(ex, "_load_policies", forbidden)
    monkeypatch.setattr(ev, "generate_scenario", forbidden)
    output = tmp_path / "heldout"
    with pytest.raises(PermissionError, match="not frozen"):
        ex.run_evaluation_shard(
            archive_dir=tmp_path,
            output_dir=output,
            shard_id=0,
            source_commit_sha=SOURCE,
            workflow_commit_sha=WORKFLOW,
            origin_run_id=RUN_ID,
            resume=False,
        )
    assert not output.exists()


def test_first_run_commit_and_exact_next_only(tmp_path):
    shard = ex.evaluation_shards()[0]
    c = contract(shard)
    root = tmp_path / "shard-000"
    store = ex.EvaluationShardStore(root, shard)
    store.initialize(c)
    store.commit_scenario(rows_for(0, c), c)
    committed, history = store.load(c)
    assert committed == 1
    assert history[0]["scenario_index"] == 0
    with pytest.raises(ValueError, match="scenario row index"):
        store.commit_scenario(rows_for(2, c), c)
    with pytest.raises(FileExistsError):
        ex.EvaluationShardStore(root, shard).initialize(c)


def test_restore_fails_closed_on_orphan_or_temp_state(tmp_path):
    shard = ex.evaluation_shards()[0]
    c = contract(shard)
    root = tmp_path / "shard-000"
    store = ex.EvaluationShardStore(root, shard)
    store.initialize(c)
    orphan = store.scenario_path(0)
    orphan.parent.mkdir(parents=True)
    orphan.write_text("{}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="uncommitted scenario"):
        store.load(c)

    root2 = tmp_path / "shard-000b"
    store2 = ex.EvaluationShardStore(root2, shard)
    store2.initialize(c)
    (store2.state_dir / "ambiguous.tmp").write_text("x", encoding="utf-8")
    with pytest.raises(RuntimeError, match="temporary"):
        store2.load(c)


def test_restore_rejects_missing_or_mutated_committed_evidence(tmp_path):
    shard = ex.evaluation_shards()[0]
    c = contract(shard)
    root = tmp_path / "shard-000"
    store = ex.EvaluationShardStore(root, shard)
    store.initialize(c)
    store.commit_scenario(rows_for(0, c), c)
    path = store.scenario_path(0)
    original = path.read_text()
    path.write_text(original + "{}\n")
    with pytest.raises(ValueError, match="digest"):
        store.load(c)
    path.write_text(original)
    path.unlink()
    with pytest.raises(FileNotFoundError, match="missing"):
        store.load(c)


def test_contract_is_exact_and_resume_cannot_substitute_origin(tmp_path):
    shard = ex.evaluation_shards()[0]
    c = contract(shard)
    root = tmp_path / "shard-000"
    store = ex.EvaluationShardStore(root, shard)
    store.initialize(c)
    altered = dict(c)
    altered["origin_run_id"] += 1
    with pytest.raises(ValueError, match="contract"):
        store.load(altered)


def test_finalize_requires_complete_shard(tmp_path):
    shard = ex.evaluation_shards()[0]
    c = contract(shard)
    root = tmp_path / "shard-000"
    store = ex.EvaluationShardStore(root, shard)
    store.initialize(c)
    with pytest.raises(ValueError, match="incomplete"):
        store.finalize(c)
    for index in shard.scenario_indices:
        store.commit_scenario(rows_for(index, c), c)
    complete = store.finalize(c)
    assert complete["committed_scenarios"] == 5
    assert complete["rows"] == 90


def test_row_contract_rejects_duplicate_combination():
    c = contract()
    rows = rows_for(0, c)
    rows[-1] = dict(rows[-2])
    with pytest.raises(ValueError, match="exact 18"):
        ex.validate_scenario_rows(rows, 0, c)


def test_collector_rejects_incomplete_shard_set(tmp_path):
    with pytest.raises(ValueError, match="40"):
        ex.collect_evaluation_shards(
            [],
            output_file=tmp_path / "panel.jsonl",
            source_commit_sha=SOURCE,
            workflow_commit_sha=WORKFLOW,
            origin_run_id=RUN_ID,
        )


def test_completed_shard_finalize_is_idempotent_for_resume(tmp_path):
    shard = ex.evaluation_shards()[0]
    c = contract(shard)
    root = tmp_path / "shard-000"
    store = ex.EvaluationShardStore(root, shard)
    store.initialize(c)
    for index in shard.scenario_indices:
        real_rows = rows_for(index, c)
        registry = {(e["regime"], e["training_seed"]): e for e in ev.frozen_registry()["entries"]}
        for row in real_rows:
            if row["training_seed"] is not None:
                row["checkpoint_sha256"] = registry[row["regime"], row["training_seed"]]["final_checkpoint_sha256"]
        store.commit_scenario(real_rows, c)
    first = store.finalize(c)
    second = store.finalize(c)
    assert first == second


def test_row_validation_binds_frozen_seed_and_checkpoint(tmp_path):
    c = contract()
    rows = rows_for(0, c)
    registry = {(e["regime"], e["training_seed"]): e for e in ev.frozen_registry()["entries"]}
    for row in rows:
        if row["training_seed"] is not None:
            row["checkpoint_sha256"] = registry[row["regime"], row["training_seed"]]["final_checkpoint_sha256"]
    ex.validate_scenario_rows(rows, 0, c)
    wrong_seed = [dict(row) for row in rows]
    for row in wrong_seed:
        row["evaluation_scenario_seed"] = "123"
    with pytest.raises(ValueError, match="frozen schedule"):
        ex.validate_scenario_rows(wrong_seed, 0, c)
    wrong_checkpoint = [dict(row) for row in rows]
    next(row for row in wrong_checkpoint if row["training_seed"] is not None)["checkpoint_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="checkpoint provenance"):
        ex.validate_scenario_rows(wrong_checkpoint, 0, c)


def test_history_path_cannot_escape_frozen_layout(tmp_path):
    shard = ex.evaluation_shards()[0]
    c = contract(shard)
    root = tmp_path / "shard-000"
    store = ex.EvaluationShardStore(root, shard)
    store.initialize(c)
    rows = rows_for(0, c)
    registry = {(e["regime"], e["training_seed"]): e for e in ev.frozen_registry()["entries"]}
    for row in rows:
        if row["training_seed"] is not None:
            row["checkpoint_sha256"] = registry[row["regime"], row["training_seed"]]["final_checkpoint_sha256"]
    store.commit_scenario(rows, c)
    latest = json.loads(store.latest_path.read_text())
    latest["history"][0]["file"] = "../outside.jsonl"
    store.latest_path.write_text(json.dumps(latest), encoding="utf-8")
    with pytest.raises(ValueError, match="frozen layout"):
        store.load(c)


def test_monolithic_final_evaluation_path_is_permanently_disabled(tmp_path):
    with pytest.raises(PermissionError, match="Monolithic"):
        ev.run_final_evaluation(tmp_path, tmp_path / "out", SOURCE)
