from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from paper2_model0.ai.launcher import locked_job_registry


FROZEN_LAUNCHER_SHA = "fb4f386703294990917e9d99e10013925a9a54d6"
FROZEN_WORKFLOW_REF = "refs/heads/ai-full-training-v0.1-frozen"
FROZEN_REPOSITORY = "plinhnguyende-svg/Paper-2-model0"
WORKFLOW_PATH = Path(".github/workflows/ai_full_training_v0.1.yml")
SCRIPT_PATH = Path("scripts/run_ai_full_training_job.py")
REQUIREMENTS_PATH = Path("requirements-ai-training-v0.1.txt")
CONSTRAINTS_PATH = Path("constraints-ai-training-v0.1.txt")


def _workflow():
    return yaml.load(
        WORKFLOW_PATH.read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )


def _load_entrypoint(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _set_workflow_env(monkeypatch, *, sha: str = "2" * 40):
    monkeypatch.setenv("PAPER2_AI_FULL_TRAINING_AUTHORIZED", "YES")
    monkeypatch.setenv("PAPER2_AI_FROZEN_LAUNCHER_SHA", FROZEN_LAUNCHER_SHA)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_REPOSITORY", FROZEN_REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", FROZEN_WORKFLOW_REF)
    monkeypatch.setenv("GITHUB_SHA", sha)
    monkeypatch.setenv("GITHUB_RUN_ID", "1")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")


def test_full_training_workflow_is_manual_only_and_has_only_operational_inputs():
    workflow = _workflow()
    assert set(workflow["on"]) == {"workflow_dispatch"}
    dispatch = workflow["on"]["workflow_dispatch"]
    assert set(dispatch["inputs"]) == {"confirmation", "resume_run_id"}

    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "schedule:" not in text
    assert "RUN_FROZEN_AI_V0_1" in text
    assert f'test "${{GITHUB_REF}}" = "{FROZEN_WORKFLOW_REF}"' in text

    for forbidden_input in (
        "episodes:",
        "episode_count:",
        "horizon:",
        "learning_rate:",
        "gamma:",
        "device:",
        "simulation_config:",
    ):
        assert forbidden_input not in text


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


def test_github_actions_are_commit_pinned_not_mutable_major_tags():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "actions/checkout@11d5960a326750d5838078e36cf38b85af677262" in text
    assert "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065" in text
    assert "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093" in text
    assert "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02" in text
    for mutable in (
        "actions/checkout@v4\n",
        "actions/setup-python@v5\n",
        "actions/download-artifact@v4\n",
        "actions/upload-artifact@v4\n",
    ):
        assert mutable not in text


def test_workflow_locks_runtime_authorization_and_exact_checkout_sha():
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
    assert env["NUMEXPR_NUM_THREADS"] == "1"
    assert env["PYTHONHASHSEED"] == "0"
    assert env["PYTHONPATH"] == "src"

    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'python-version: "3.12.14"' in text
    assert "pip==26.2.1" in text
    assert "requirements-ai-training-v0.1.txt" in text
    assert "constraints-ai-training-v0.1.txt" in text
    assert "python -m pip check" in text
    assert "python -m pip install -e ." not in text
    assert "ref: ${{ github.sha }}" in text


def test_locked_direct_and_transitive_requirement_versions_are_exact():
    direct = {
        line.strip()
        for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    assert direct == {
        "numpy==2.5.3",
        "pandas==3.0.6",
        "PyYAML==6.0.3",
        "torch==2.14.0",
    }

    constraints = [
        line.strip()
        for line in CONSTRAINTS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert constraints
    assert all("==" in line for line in constraints)
    required_transitive = {
        "filelock==4.0.0",
        "fsspec==2026.7.0",
        "Jinja2==3.1.6",
        "networkx==3.6.1",
        "sympy==1.14.0",
        "triton==3.8.0",
        "typing-extensions==4.16.0",
        "nvidia-cudnn==9.24.0.43",
        "nvidia-cublas==13.1.1.3",
    }
    assert required_transitive.issubset(set(constraints))


def test_resume_requires_named_prior_artifact_and_preserves_upload_buffer():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "run-id: ${{ inputs.resume_run_id }}" in text
    assert "--require-existing-state" in text
    assert "continue-on-error" not in text
    assert "if: ${{ always() }}" in text
    assert "if-no-files-found: error" in text
    assert "retention-days: 90" in text

    job = _workflow()["jobs"]["train"]
    train_step = next(
        step for step in job["steps"]
        if step["name"] == "Run frozen scientific training job"
    )
    assert train_step["timeout-minutes"] == "300"
    assert int(train_step["timeout-minutes"]) < int(job["timeout-minutes"])


def test_entrypoint_has_no_scientific_override_arguments_and_requires_frozen_context():
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
    assert FROZEN_WORKFLOW_REF in text
    assert FROZEN_REPOSITORY in text
    assert "torch.use_deterministic_algorithms(True)" in text
    assert "torch.set_num_threads(1)" in text
    assert "current_pip_freeze" in text
    assert "validate_restored_provenance" in text


def test_entrypoint_runtime_validator_is_exact(monkeypatch):
    module = _load_entrypoint("run_ai_full_training_job_runtime")
    monkeypatch.setattr(module.platform, "python_version", lambda: "3.12.14")
    monkeypatch.setattr(module.np, "__version__", "2.5.3")
    monkeypatch.setattr(module.pd, "__version__", "3.0.6")
    monkeypatch.setattr(module.yaml, "__version__", "6.0.3")
    monkeypatch.setattr(module.torch, "__version__", "2.14.0")
    module.validate_frozen_runtime_versions()

    monkeypatch.setattr(module.platform, "python_version", lambda: "3.12.13")
    with pytest.raises(RuntimeError, match="runtime version drift"):
        module.validate_frozen_runtime_versions()


def test_entrypoint_validation_does_not_train(monkeypatch, tmp_path):
    module = _load_entrypoint("run_ai_full_training_job")
    monkeypatch.setattr(module, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(module, "validate_frozen_runtime_versions", lambda: None)
    _set_workflow_env(monkeypatch)

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
    payload = json.loads(provenance[0].read_text(encoding="utf-8"))
    assert payload["workflow_ref"] == FROZEN_WORKFLOW_REF
    assert payload["workflow_execution_sha"] == "2" * 40
    assert payload["frozen_launcher_sha"] == FROZEN_LAUNCHER_SHA
    assert payload["pip_freeze_sha256"]
    assert (provenance[0].parent / "pip-freeze.txt").exists()


def test_entrypoint_rejects_non_frozen_workflow_context(monkeypatch, tmp_path):
    module = _load_entrypoint("run_ai_full_training_job_bad_context")
    monkeypatch.setattr(module, "OUTPUT_ROOT", tmp_path)
    _set_workflow_env(monkeypatch)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")

    with pytest.raises(RuntimeError, match="frozen workflow ref"):
        module.main(
            [
                "--regime", "N",
                "--training-seed", "41001",
                "--validate-only",
            ]
        )


def test_resume_flags_must_be_supplied_together(monkeypatch, tmp_path):
    module = _load_entrypoint("run_ai_full_training_job_resume_pair")
    monkeypatch.setattr(module, "OUTPUT_ROOT", tmp_path)
    _set_workflow_env(monkeypatch)

    with pytest.raises(ValueError, match="supplied together"):
        module.main(
            [
                "--regime", "N",
                "--training-seed", "41001",
                "--validate-only",
                "--resume-run-id", "12345",
            ]
        )


def test_resume_provenance_is_bound_to_same_workflow_sha_and_runtime(
    monkeypatch,
    tmp_path,
):
    module = _load_entrypoint("run_ai_full_training_job_resume_provenance")
    monkeypatch.setattr(module, "OUTPUT_ROOT", tmp_path)
    _set_workflow_env(monkeypatch, sha="3" * 40)

    job = module.locked_job("N", 41001)
    freeze_text, freeze_sha = module.current_pip_freeze()
    provenance_dir = tmp_path / job.relative_directory / "provenance"
    provenance_dir.mkdir(parents=True, exist_ok=True)
    (provenance_dir / "pip-freeze.txt").write_text(
        freeze_text,
        encoding="utf-8",
    )
    prior = {
        "frozen_launcher_sha": FROZEN_LAUNCHER_SHA,
        "workflow_execution_sha": "3" * 40,
        "workflow_ref": FROZEN_WORKFLOW_REF,
        "workflow_repository": FROZEN_REPOSITORY,
        "workflow_run_id": "12345",
        "workflow_run_attempt": "1",
        "regime": "N",
        "training_seed": 41001,
        "pip_freeze_sha256": freeze_sha,
        **module.current_contract_file_hashes(),
    }
    (provenance_dir / "workflow_run_12345_attempt_1.json").write_text(
        json.dumps(prior, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    module.validate_restored_provenance(
        job,
        resume_run_id="12345",
        current_pip_freeze_sha256=freeze_sha,
    )

    monkeypatch.setenv("GITHUB_SHA", "4" * 40)
    with pytest.raises(ValueError, match="workflow_execution_sha"):
        module.validate_restored_provenance(
            job,
            resume_run_id="12345",
            current_pip_freeze_sha256=freeze_sha,
        )


def test_resume_validation_requires_existing_latest_pointer(monkeypatch, tmp_path):
    module = _load_entrypoint("run_ai_full_training_job_resume")
    monkeypatch.setattr(module, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(module, "validate_frozen_runtime_versions", lambda: None)
    _set_workflow_env(monkeypatch, sha="5" * 40)

    job = module.locked_job("N", 41001)
    freeze_text, freeze_sha = module.current_pip_freeze()
    provenance_dir = tmp_path / job.relative_directory / "provenance"
    provenance_dir.mkdir(parents=True, exist_ok=True)
    (provenance_dir / "pip-freeze.txt").write_text(
        freeze_text,
        encoding="utf-8",
    )
    prior = {
        "frozen_launcher_sha": FROZEN_LAUNCHER_SHA,
        "workflow_execution_sha": "5" * 40,
        "workflow_ref": FROZEN_WORKFLOW_REF,
        "workflow_repository": FROZEN_REPOSITORY,
        "workflow_run_id": "12345",
        "workflow_run_attempt": "1",
        "regime": "N",
        "training_seed": 41001,
        "pip_freeze_sha256": freeze_sha,
        **module.current_contract_file_hashes(),
    }
    (provenance_dir / "workflow_run_12345_attempt_1.json").write_text(
        json.dumps(prior, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="latest.json"):
        module.main(
            [
                "--regime", "N",
                "--training-seed", "41001",
                "--validate-only",
                "--require-existing-state",
                "--resume-run-id", "12345",
            ]
        )
