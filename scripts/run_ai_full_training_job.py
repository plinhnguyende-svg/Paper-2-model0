from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

import numpy as np
import pandas as pd
import torch
import yaml

from paper2_model0.ai.launcher import (
    FROZEN_LAUNCHER_SHA_ENV,
    FULL_TRAINING_AUTH_ENV,
    LauncherRunStore,
    locked_job,
    locked_simulation_config,
    run_locked_training_job,
    validate_launcher_config,
    validate_launcher_device,
)


FROZEN_LAUNCHER_SHA = "fb4f386703294990917e9d99e10013925a9a54d6"
FROZEN_WORKFLOW_REF = "refs/heads/ai-full-training-v0.1-frozen"
FROZEN_REPOSITORY = "plinhnguyende-svg/Paper-2-model0"
OUTPUT_ROOT = Path("outputs/ai_full_training_v0.1")
WORKFLOW_PATH = Path(".github/workflows/ai_full_training_v0.1.yml")
ENTRYPOINT_PATH = Path("scripts/run_ai_full_training_job.py")
REQUIREMENTS_PATH = Path("requirements-ai-training-v0.1.txt")
CONSTRAINTS_PATH = Path("constraints-ai-training-v0.1.txt")
CONFIRMATION_PHRASE = "RUN_FROZEN_AI_V0_1"


def configure_deterministic_runtime() -> None:
    torch.set_num_threads(1)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)


def validate_authorization_environment() -> None:
    if os.environ.get(FULL_TRAINING_AUTH_ENV) != "YES":
        raise RuntimeError("full-training authorization variable is not enabled")
    if os.environ.get(FROZEN_LAUNCHER_SHA_ENV, "").strip().lower() != FROZEN_LAUNCHER_SHA:
        raise RuntimeError("workflow frozen-launcher SHA does not match the audited launcher")


def validate_workflow_context() -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("scientific training must execute inside GitHub Actions")
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise RuntimeError("scientific training requires workflow_dispatch")
    if os.environ.get("GITHUB_REPOSITORY") != FROZEN_REPOSITORY:
        raise RuntimeError("scientific training repository context drift")
    if os.environ.get("GITHUB_REF") != FROZEN_WORKFLOW_REF:
        raise RuntimeError("scientific training must use the frozen workflow ref")
    execution_sha = os.environ.get("GITHUB_SHA", "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", execution_sha):
        raise RuntimeError("workflow execution SHA must be a full git SHA")


def validate_frozen_runtime_versions() -> None:
    expected = {
        "python": "3.12.14",
        "numpy": "2.5.3",
        "pandas": "3.0.6",
        "pyyaml": "6.0.3",
        "torch": "2.14.0",
    }
    observed = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "pyyaml": yaml.__version__,
        "torch": torch.__version__,
    }
    if observed != expected:
        raise RuntimeError(
            f"frozen scientific runtime version drift: {observed!r}"
        )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def current_contract_file_hashes() -> dict[str, str]:
    return {
        "workflow_sha256": _file_sha256(WORKFLOW_PATH),
        "entrypoint_sha256": _file_sha256(ENTRYPOINT_PATH),
        "requirements_sha256": _file_sha256(REQUIREMENTS_PATH),
        "constraints_sha256": _file_sha256(CONSTRAINTS_PATH),
    }


def current_pip_freeze() -> tuple[str, str]:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "--disable-pip-version-check",
            "freeze",
            "--all",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    lines = sorted(
        {
            line.strip()
            for line in completed.stdout.splitlines()
            if line.strip()
        },
        key=str.casefold,
    )
    text = "\n".join(lines) + "\n"
    return text, _sha256_bytes(text.encode("utf-8"))


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def provenance_path(job) -> Path:
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "0")
    return (
        OUTPUT_ROOT
        / job.relative_directory
        / "provenance"
        / f"workflow_run_{run_id}_attempt_{attempt}.json"
    )


def runtime_lock_path(job) -> Path:
    return OUTPUT_ROOT / job.relative_directory / "provenance" / "pip-freeze.txt"


def validate_restored_provenance(
    job,
    *,
    resume_run_id: str,
    current_pip_freeze_sha256: str,
) -> None:
    if not re.fullmatch(r"[1-9][0-9]*", resume_run_id):
        raise ValueError("resume_run_id must be a positive integer")

    provenance_dir = OUTPUT_ROOT / job.relative_directory / "provenance"
    candidates = sorted(
        provenance_dir.glob(f"workflow_run_{resume_run_id}_attempt_*.json")
    )
    if not candidates:
        raise FileNotFoundError(
            "restored artifact is missing provenance for resume_run_id"
        )

    def attempt_number(path: Path) -> int:
        match = re.fullmatch(
            rf"workflow_run_{re.escape(resume_run_id)}_attempt_([0-9]+)\.json",
            path.name,
        )
        if match is None:
            raise ValueError("invalid restored provenance filename")
        return int(match.group(1))

    previous_path = max(candidates, key=attempt_number)
    previous = _read_json(previous_path)
    expected = {
        "frozen_launcher_sha": FROZEN_LAUNCHER_SHA,
        "workflow_execution_sha": os.environ["GITHUB_SHA"].strip().lower(),
        "workflow_ref": FROZEN_WORKFLOW_REF,
        "workflow_repository": FROZEN_REPOSITORY,
        "workflow_run_id": resume_run_id,
        "regime": job.regime,
        "training_seed": job.training_seed,
    }
    for key, value in expected.items():
        if previous.get(key) != value:
            raise ValueError(f"restored provenance mismatch for {key}")

    for key, digest in current_contract_file_hashes().items():
        if previous.get(key) != digest:
            raise ValueError(f"restored provenance contract hash drift for {key}")

    previous_freeze_sha = previous.get("pip_freeze_sha256")
    if previous_freeze_sha != current_pip_freeze_sha256:
        raise ValueError("restored runtime environment differs from current runtime")

    lock_path = runtime_lock_path(job)
    if not lock_path.exists():
        raise FileNotFoundError("restored artifact is missing pip-freeze.txt")
    if _file_sha256(lock_path) != previous_freeze_sha:
        raise ValueError("restored pip-freeze.txt does not match prior provenance")


def write_runtime_lock(job, text: str) -> Path:
    destination = runtime_lock_path(job)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return destination


def write_execution_provenance(
    job,
    *,
    resume_run_id: str | None,
    pip_freeze_sha256: str,
) -> Path:
    destination = provenance_path(job)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "frozen_launcher_sha": FROZEN_LAUNCHER_SHA,
        "workflow_execution_sha": os.environ.get("GITHUB_SHA", "").strip().lower(),
        "workflow_ref": os.environ.get("GITHUB_REF", ""),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "workflow_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "workflow_repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "regime": job.regime,
        "training_seed": job.training_seed,
        "resume_run_id": resume_run_id or "",
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "torch_version": torch.__version__,
        "torch_deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "torch_num_threads": torch.get_num_threads(),
        "runner_image_os": os.environ.get("ImageOS", ""),
        "runner_image_version": os.environ.get("ImageVersion", ""),
        "platform": platform.platform(),
        "pip_freeze_sha256": pip_freeze_sha256,
        "scientific_output_root": str(OUTPUT_ROOT),
        **current_contract_file_hashes(),
    }
    destination.write_text(
        json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return destination


def validate_operational_state(job, *, require_existing_state: bool) -> None:
    config = locked_simulation_config()
    validate_launcher_config(config)
    validate_launcher_device("cpu")

    store = LauncherRunStore(OUTPUT_ROOT, job)
    if not require_existing_state:
        return
    if not store.latest_path.exists():
        raise FileNotFoundError(
            "resume was requested but the restored artifact has no latest.json"
        )
    store.load_committed_state(
        config=config,
        source_commit_sha=FROZEN_LAUNCHER_SHA,
        device="cpu",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute one job from the frozen 15-run AI training registry."
    )
    parser.add_argument("--regime", required=True, choices=("N", "S", "F"))
    parser.add_argument("--training-seed", required=True, type=int)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--require-existing-state", action="store_true")
    parser.add_argument("--resume-run-id", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if bool(args.resume_run_id) != bool(args.require_existing_state):
        raise ValueError(
            "resume_run_id and --require-existing-state must be supplied together"
        )
    job = locked_job(args.regime, args.training_seed)

    validate_authorization_environment()
    validate_workflow_context()
    validate_frozen_runtime_versions()
    configure_deterministic_runtime()

    pip_freeze_text, pip_freeze_sha256 = current_pip_freeze()
    if args.resume_run_id:
        validate_restored_provenance(
            job,
            resume_run_id=args.resume_run_id,
            current_pip_freeze_sha256=pip_freeze_sha256,
        )

    validate_operational_state(
        job,
        require_existing_state=bool(args.require_existing_state),
    )
    write_runtime_lock(job, pip_freeze_text)
    write_execution_provenance(
        job,
        resume_run_id=args.resume_run_id or None,
        pip_freeze_sha256=pip_freeze_sha256,
    )

    if args.validate_only:
        print(
            f"validated frozen scientific job {job.job_id}; "
            "no training executed"
        )
        return 0

    report = run_locked_training_job(
        output_root=OUTPUT_ROOT,
        job=job,
        source_commit_sha=FROZEN_LAUNCHER_SHA,
    )
    result_path = OUTPUT_ROOT / job.relative_directory / "workflow_result.json"
    result_path.write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"completed frozen scientific job {job.job_id}: "
        f"{report['label']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
