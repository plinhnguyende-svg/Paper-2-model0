from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

from paper2_model0.ai.launcher import locked_job_registry


FROZEN_LAUNCHER_SHA = "fb4f386703294990917e9d99e10013925a9a54d6"
WORKFLOW_PATH = Path(".github/workflows/ai_full_training_v0.1.yml")
SCRIPT_PATH = Path("scripts/run_ai_full_training_job.py")
REQUIREMENTS_PATH = Path("requirements-ai-training-v0.1.txt")


def _workflow():
    return yaml.load(
        WORKFLOW_PATH.read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )


def test_full_training_workflow_is_manual_only():
    workflow = _workflow()
    assert set(workflow["on"]) == {"workflow_dispatch"}
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "schedule:" not in text
    assert "RUN_FROZEN_AI_V0_1" in text
    assert 'test "${GITHUB_REF}" = "refs/heads/main"' in text


def test_workflow_matrix_is_exact_frozen_15_job_registry():
    workflow = _workflow()
    strategy = workflow["jobs"]["train"]["strategy"]
    assert strategy["fail-fast"] == "false"
    assert strategy["max-parallel"] == "5"

    included = strategy["matrix"]["include"]
    matrix_keys = tuple(
        (row["regime"], int(row["training_seed"]))
        for row in included
    )
    launcher_keys = tuple(
        (job.regime, job.training_seed)
        for job in locked_job_registry()
    )
    assert matrix_keys == launcher_keys
    assert len(set(matrix_keys)) == 15


def test_workflow_locks_runtime_and_launcher_authorization():
    workflow = _workflow()
    job = workflow["jobs"]["train"]
    assert job["runs-on"] == "ubuntu-24.04"
    assert job["timeout-minutes"] == "330"

    env = job["env"]
    assert env["PAPER2_AI_FULL_TRAINING_AUTHORIZED"] == "YES"
    assert env["PAPER2_AI_FROZEN_LAUNCHER_SHA"] == FROZEN_LAUNCHER_SHA
    assert env["OMP_NUM_THREADS"] == "1"
    assert env["MKL_NUM_THREADS"] == "1"
    assert env["OPENBLAS_NUM_THREADS"] == "1"
    assert env["PYTHONHASHSEED"] == "0"

    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'python-version: "3.12.14"' in text
    assert "requirements-ai-training-v0.1.txt" in text
    assert "python -m pip install -e . --no-deps" in text


def test_locked_requirement_versions_are_exact():
    lines = {
        line.strip()
        for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    assert lines == {
        "numpy==2.5.3",
        "pandas==3.0.6",
        "PyYAML==6.0.3",
        "torch==2.14.0",
    }


def test_resume_requires_named_prior_artifact_and_never_falls_back_to_fresh():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "actions/download-artifact@v4" in text
    assert "run-id: ${{ inputs.resume_run_id }}" in text
    assert "--require-existing-state" in text
    assert "continue-on-error" not in text
    assert "actions/upload-artifact@v4" in text
    assert "if: ${{ always() }}" in text
    assert "if-no-files-found: error" in text

    job = _workflow()["jobs"]["train"]
    train_step = next(
        step for step in job["steps"]
        if step["name"] == "Run frozen scientific training job"
    )
    assert train_step["timeout-minutes"] == "300"
    assert int(train_step["timeout-minutes"]) < int(job["timeout-minutes"])


def test_entrypoint_has_no_scientific_override_arguments():
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "--episodes",
        "--episode-count",
        "--horizon",
        "--config",
        "--learning-rate",
        "--gamma",
        "--ppo",
        "--device",
    ):
        assert forbidden not in text
    assert FROZEN_LAUNCHER_SHA in text
    assert "torch.use_deterministic_algorithms(True)" in text
    assert "torch.set_num_threads(1)" in text


def test_entrypoint_validation_does_not_train(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location(
        "run_ai_full_training_job",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    monkeypatch.setattr(module, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setenv("PAPER2_AI_FULL_TRAINING_AUTHORIZED", "YES")
    monkeypatch.setenv("PAPER2_AI_FROZEN_LAUNCHER_SHA", FROZEN_LAUNCHER_SHA)
    monkeypatch.setenv("GITHUB_RUN_ID", "1")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_SHA", "2" * 40)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")

    called = {"training": False}

    def forbidden_training(**kwargs):
        called["training"] = True
        raise AssertionError("validate-only path must not train")

    monkeypatch.setattr(module, "run_locked_training_job", forbidden_training)
    rc = module.main(
        [
            "--regime", "N",
            "--training-seed", "41001",
            "--validate-only",
        ]
    )
    assert rc == 0
    assert called["training"] is False
    provenance = list(
        (tmp_path / "regime_N" / "seed_41001" / "provenance").glob("*.json")
    )
    assert len(provenance) == 1


def test_resume_validation_requires_existing_latest_pointer(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location(
        "run_ai_full_training_job_resume",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    monkeypatch.setattr(module, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setenv("PAPER2_AI_FULL_TRAINING_AUTHORIZED", "YES")
    monkeypatch.setenv("PAPER2_AI_FROZEN_LAUNCHER_SHA", FROZEN_LAUNCHER_SHA)

    with pytest.raises(FileNotFoundError, match="resume was requested"):
        module.main(
            [
                "--regime", "N",
                "--training-seed", "41001",
                "--validate-only",
                "--require-existing-state",
                "--resume-run-id", "12345",
            ]
        )
