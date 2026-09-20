from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil

import pytest
import yaml

from paper2_model0.ai import evaluation as ev
from paper2_model0.ai import evaluation_execution as ex
from paper2_model0.ai.training_protocol import INFORMATION_REGIMES, TRAINING_SEEDS


WORKFLOW_PATH = Path(".github/workflows/ai_final_evaluation_v0.1.yml")
GUARD_PATH = Path("scripts/ai_evaluation_workflow_guard.py")
EVALUATOR_SHA = "9e42c4a39e6bc8be94d1ed44e993899e4d916481"
FROZEN_REF = "refs/heads/ai-final-evaluation-v0.1-frozen"
REPOSITORY = "plinhnguyende-svg/Paper-2-model0"
WORKFLOW_REF = (
    f"{REPOSITORY}/.github/workflows/ai_final_evaluation_v0.1.yml@{FROZEN_REF}"
)
WORKFLOW_SHA = "7" * 40


def _guard():
    spec = importlib.util.spec_from_file_location("ai_evaluation_workflow_guard", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _workflow():
    return yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _control_root(tmp_path: Path) -> Path:
    root = tmp_path / "control"
    target = root / ".github/workflows/ai_final_evaluation_v0.1.yml"
    target.parent.mkdir(parents=True)
    shutil.copy2(WORKFLOW_PATH, target)
    return root


def _set_env(monkeypatch, *, run_id: int, run_attempt: int = 1, workflow_sha: str = WORKFLOW_SHA):
    values = {
        "PAPER2_AI_FINAL_EVALUATION_AUTHORIZED": "YES",
        "PAPER2_AI_FROZEN_EVALUATOR_SHA": EVALUATOR_SHA,
        "PAPER2_AI_FROZEN_WORKFLOW_SHA": workflow_sha,
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_REF": FROZEN_REF,
        "GITHUB_WORKFLOW_REF": WORKFLOW_REF,
        "GITHUB_SHA": workflow_sha,
        "GITHUB_WORKFLOW_SHA": workflow_sha,
        "GITHUB_RUN_ID": str(run_id),
        "GITHUB_RUN_ATTEMPT": str(run_attempt),
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def _rows(index: int, source_sha: str) -> list[dict]:
    rows = []
    seed = str(ev.evaluation_seed_schedule()[index])
    registry = {
        (entry["regime"], int(entry["training_seed"])): entry
        for entry in ev.frozen_registry()["entries"]
    }
    for regime in INFORMATION_REGIMES:
        for training_seed in (None, *TRAINING_SEEDS):
            rows.append(
                {
                    "scenario_index": index,
                    "scenario_id": f"synthetic-workflow-{index}",
                    "evaluation_scenario_seed": seed,
                    "regime": regime,
                    "decision_architecture": "RuleBased" if training_seed is None else "AI",
                    "training_seed": training_seed,
                    "checkpoint_sha256": (
                        None
                        if training_seed is None
                        else registry[regime, training_seed]["final_checkpoint_sha256"]
                    ),
                    "source_sha": source_sha,
                    "registry_sha256": ev.REGISTRY_SHA256,
                    **{
                        metric: float(index + 1)
                        for metric in ev.PRIMARY + ev.SECONDARY
                    },
                }
            )
    assert len(rows) == 18
    return rows


def _resume_manifest(monkeypatch, tmp_path: Path):
    guard = _guard()
    control = _control_root(tmp_path)
    _set_env(monkeypatch, run_id=90001)
    prior_path = tmp_path / "prior.json"
    prior = guard.prepare_run(control_root=control, output=prior_path)
    assert prior["origin_run_id"] == 90001

    _set_env(monkeypatch, run_id=90002)
    current_path = tmp_path / "current.json"
    current = guard.prepare_run(
        control_root=control,
        output=current_path,
        resume_run_id=90001,
        prior_manifest=prior_path,
    )
    assert current["origin_run_id"] == 90001
    assert current["resume_from_run_id"] == 90001
    return guard, control, current_path, current


def test_workflow_is_manual_only_and_exposes_no_scientific_inputs():
    workflow = _workflow()
    assert set(workflow["on"]) == {"workflow_dispatch"}
    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"confirmation", "resume_run_id"}

    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "schedule:" not in text
    assert "RUN_FROZEN_AI_EVALUATION_V0_1" in text
    assert 'test "${GITHUB_RUN_ATTEMPT}" = "1"' in text
    for forbidden in (
        "scenario_count",
        "evaluation_seed",
        "training_seed",
        "regime",
        "horizon",
        "warmup",
        "shelf_life",
        "learning_rate",
        "bootstrap_seed",
    ):
        assert forbidden not in inputs


def test_workflow_static_matrix_and_exact_frozen_evaluator_checkout():
    workflow = _workflow()
    assert set(workflow["jobs"]) == {"prepare", "evaluate", "collect"}
    strategy = workflow["jobs"]["evaluate"]["strategy"]
    assert strategy["fail-fast"] == "false"
    assert strategy["max-parallel"] == "5"
    matrix = strategy["matrix"]["include"]
    assert [(int(row["shard_id"]), row["shard_name"]) for row in matrix] == [
        (i, f"shard-{i:03d}") for i in range(40)
    ]

    env = workflow["env"]
    assert env["PAPER2_AI_FINAL_EVALUATION_AUTHORIZED"] == "YES"
    assert env["PAPER2_AI_FROZEN_EVALUATOR_SHA"] == EVALUATOR_SHA
    assert env["PAPER2_AI_FROZEN_WORKFLOW_SHA"] == "${{ github.workflow_sha }}"

    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert text.count(f'ref: "{EVALUATOR_SHA}"') == 3
    assert text.count("ref: ${{ github.workflow_sha }}") == 3
    assert FROZEN_REF in text
    assert len(matrix) == 40
    assert "3,600-row panel" in text


def test_actions_runtime_and_upload_recovery_are_pinned():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    for action in (
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
    ):
        assert action in text
    for mutable in (
        "actions/checkout@v4",
        "actions/setup-python@v5",
        "actions/download-artifact@v4",
        "actions/upload-artifact@v4",
    ):
        assert mutable not in text
    assert 'python-version: "3.12.14"' in text
    assert 'pip==26.2.1' in text
    assert 'OMP_NUM_THREADS: "1"' in text
    assert 'MKL_NUM_THREADS: "1"' in text
    assert 'OPENBLAS_NUM_THREADS: "1"' in text
    assert 'NUMEXPR_NUM_THREADS: "1"' in text
    assert 'PYTHONHASHSEED: "0"' in text
    assert "if: ${{ always() }}" in text
    assert "if-no-files-found: error" in text
    assert "timeout-minutes: 300" in text
    assert "timeout-minutes: 330" in text


def test_workflow_blob_is_bound_by_guard():
    guard = _guard()
    assert guard.FROZEN_WORKFLOW_BLOB_SHA == guard._git_blob_sha(WORKFLOW_PATH)


def test_first_run_and_resume_preserve_origin_and_bind_parent(monkeypatch, tmp_path):
    guard = _guard()
    control = _control_root(tmp_path)
    _set_env(monkeypatch, run_id=81001)
    first_path = tmp_path / "first.json"
    first = guard.prepare_run(control_root=control, output=first_path)
    assert first["origin_run_id"] == 81001
    assert first["resume_from_run_id"] is None
    assert first["parent_manifest_sha256"] is None
    assert guard.validate_current_run(control_root=control, manifest_path=first_path) == first

    _set_env(monkeypatch, run_id=81002)
    resumed_path = tmp_path / "resumed.json"
    resumed = guard.prepare_run(
        control_root=control,
        output=resumed_path,
        resume_run_id=81001,
        prior_manifest=first_path,
    )
    assert resumed["origin_run_id"] == 81001
    assert resumed["resume_from_run_id"] == 81001
    assert len(resumed["parent_manifest_sha256"]) == 64
    assert guard.validate_current_run(control_root=control, manifest_path=resumed_path) == resumed


def test_wrong_prior_run_wrong_ref_wrong_sha_and_rerun_fail_closed(monkeypatch, tmp_path):
    guard = _guard()
    control = _control_root(tmp_path)
    _set_env(monkeypatch, run_id=82001)
    prior_path = tmp_path / "prior.json"
    guard.prepare_run(control_root=control, output=prior_path)

    _set_env(monkeypatch, run_id=82002)
    with pytest.raises(ValueError, match="requested resume_run_id"):
        guard.prepare_run(
            control_root=control,
            output=tmp_path / "wrong-prior.json",
            resume_run_id=99999,
            prior_manifest=prior_path,
        )

    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    with pytest.raises(PermissionError, match="frozen ref"):
        guard.validate_environment(control)
    monkeypatch.setenv("GITHUB_REF", FROZEN_REF)

    monkeypatch.setenv("GITHUB_WORKFLOW_SHA", "8" * 40)
    with pytest.raises(PermissionError, match="workflow execution SHA"):
        guard.validate_environment(control)
    monkeypatch.setenv("GITHUB_WORKFLOW_SHA", WORKFLOW_SHA)

    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    with pytest.raises(PermissionError, match="rerun attempts are forbidden"):
        guard.validate_environment(control)


def test_partial_and_completed_shard_resume_without_heldout_generation(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        ev,
        "generate_scenario",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synthetic workflow audit must not generate held-out scenarios")
        ),
    )
    guard, _, manifest_path, manifest = _resume_manifest(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)

    partial_shard = ex.evaluation_shards()[0]
    partial_root = tmp_path / "shard-000"
    partial_contract = ex.build_execution_contract(
        shard=partial_shard,
        source_commit_sha=EVALUATOR_SHA,
        workflow_commit_sha=manifest["workflow_sha"],
        origin_run_id=manifest["origin_run_id"],
    )
    partial_store = ex.EvaluationShardStore(partial_root, partial_shard)
    partial_store.initialize(partial_contract)
    partial_store.commit_scenario(_rows(0, EVALUATOR_SHA), partial_contract)
    partial = guard.validate_restored_shard(
        control_root=tmp_path / "control",
        manifest_path=manifest_path,
        shard_dir=partial_root,
        shard_id=0,
    )
    assert partial["committed_scenarios"] == 1
    assert partial["complete"] is False

    complete_shard = ex.evaluation_shards()[1]
    complete_root = tmp_path / "shard-001"
    complete_contract = ex.build_execution_contract(
        shard=complete_shard,
        source_commit_sha=EVALUATOR_SHA,
        workflow_commit_sha=manifest["workflow_sha"],
        origin_run_id=manifest["origin_run_id"],
    )
    complete_store = ex.EvaluationShardStore(complete_root, complete_shard)
    complete_store.initialize(complete_contract)
    for index in complete_shard.scenario_indices:
        complete_store.commit_scenario(_rows(index, EVALUATOR_SHA), complete_contract)
    complete_store.finalize(complete_contract)
    complete = guard.validate_restored_shard(
        control_root=tmp_path / "control",
        manifest_path=manifest_path,
        shard_dir=complete_root,
        shard_id=1,
    )
    assert complete["committed_scenarios"] == 5
    assert complete["complete"] is True


def test_missing_resume_artifact_and_incomplete_collector_fail_closed(
    monkeypatch, tmp_path
):
    guard, _, manifest_path, _ = _resume_manifest(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError, match="prior shard artifact"):
        guard.validate_restored_shard(
            control_root=tmp_path / "control",
            manifest_path=manifest_path,
            shard_dir=tmp_path / "missing-shard",
            shard_id=0,
        )

    shard_parent = tmp_path / "collector"
    shard_parent.mkdir()
    (shard_parent / "shard-000").mkdir()
    with pytest.raises(ValueError, match="exactly the forty"):
        guard.validate_collector_set(
            control_root=tmp_path / "control",
            manifest_path=manifest_path,
            shard_parent=shard_parent,
        )


def test_full_synthetic_collector_set_is_exact_3600_rows_without_generation(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        ev,
        "generate_scenario",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synthetic workflow audit must not generate held-out scenarios")
        ),
    )
    guard, _, manifest_path, manifest = _resume_manifest(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    parent = tmp_path / "all-shards"
    for shard in ex.evaluation_shards():
        root = parent / f"shard-{shard.shard_id:03d}"
        contract = ex.build_execution_contract(
            shard=shard,
            source_commit_sha=EVALUATOR_SHA,
            workflow_commit_sha=manifest["workflow_sha"],
            origin_run_id=manifest["origin_run_id"],
        )
        store = ex.EvaluationShardStore(root, shard)
        store.initialize(contract)
        for index in shard.scenario_indices:
            store.commit_scenario(_rows(index, EVALUATOR_SHA), contract)
        store.finalize(contract)

    result = guard.validate_collector_set(
        control_root=tmp_path / "control",
        manifest_path=manifest_path,
        shard_parent=parent,
    )
    assert result == {"shards": 40, "rows": 3600}
