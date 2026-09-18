from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform

import torch

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
OUTPUT_ROOT = Path("outputs/ai_full_training_v0.1")
CONFIRMATION_PHRASE = "RUN_FROZEN_AI_V0_1"


def configure_deterministic_runtime() -> None:
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)


def validate_authorization_environment() -> None:
    if os.environ.get(FULL_TRAINING_AUTH_ENV) != "YES":
        raise RuntimeError("full-training authorization variable is not enabled")
    if os.environ.get(FROZEN_LAUNCHER_SHA_ENV, "").strip().lower() != FROZEN_LAUNCHER_SHA:
        raise RuntimeError("workflow frozen-launcher SHA does not match the audited launcher")


def provenance_path(job) -> Path:
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "0")
    return (
        OUTPUT_ROOT
        / job.relative_directory
        / "provenance"
        / f"workflow_run_{run_id}_attempt_{attempt}.json"
    )


def write_execution_provenance(job, *, resume_run_id: str | None) -> Path:
    destination = provenance_path(job)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "frozen_launcher_sha": FROZEN_LAUNCHER_SHA,
        "workflow_execution_sha": os.environ.get("GITHUB_SHA", ""),
        "workflow_ref": os.environ.get("GITHUB_REF", ""),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "workflow_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "workflow_repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "regime": job.regime,
        "training_seed": job.training_seed,
        "resume_run_id": resume_run_id or "",
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "torch_deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "torch_num_threads": torch.get_num_threads(),
        "scientific_output_root": str(OUTPUT_ROOT),
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
    if require_existing_state and not store.latest_path.exists():
        raise FileNotFoundError(
            "resume was requested but the restored artifact has no latest.json"
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
    job = locked_job(args.regime, args.training_seed)

    validate_authorization_environment()
    configure_deterministic_runtime()
    validate_operational_state(
        job,
        require_existing_state=bool(args.require_existing_state),
    )
    write_execution_provenance(
        job,
        resume_run_id=args.resume_run_id or None,
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
