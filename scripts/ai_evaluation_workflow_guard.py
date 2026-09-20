"""Operational provenance guard for the frozen final-evaluation workflow.

This module never generates a scenario and never evaluates a policy.  It only
binds GitHub workflow provenance, resume lineage, and durable shard artifacts
to the already frozen evaluator contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

FROZEN_REPOSITORY = "plinhnguyende-svg/Paper-2-model0"
FROZEN_WORKFLOW_REF = "refs/heads/ai-final-evaluation-v0.1-frozen"
FROZEN_WORKFLOW_PATH = ".github/workflows/ai_final_evaluation_v0.1.yml"
FROZEN_EVALUATOR_SHA = "9e42c4a39e6bc8be94d1ed44e993899e4d916481"
FROZEN_REGISTRY_SHA256 = "0ca89c10fc3135c577aca67f6d2ae573b72281b430218674dad5734ce72c686a"
FROZEN_WORKFLOW_BLOB_SHA = "c5be85429f673b648fe19c11095e1ff2c2bf54e7"
WORKFLOW_PROTOCOL = "ai-final-evaluation-workflow-v0.1"


def _full_sha(value: str, label: str) -> str:
    value = str(value).strip().lower()
    if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{label} must be an exact 40-character git SHA")
    return value


def _positive_int(value: Any, label: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive integer") from exc
    if parsed <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return parsed


def _read_json(path: Path) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def _atomic_json(path: Path, value: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _git_blob_sha(path: Path) -> str:
    data = Path(path).read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def _expected_workflow_ref() -> str:
    return f"{FROZEN_REPOSITORY}/{FROZEN_WORKFLOW_PATH}@{FROZEN_WORKFLOW_REF}"


def validate_environment(control_root: Path) -> dict:
    """Validate the exact manual frozen-workflow context without scientific work."""
    if os.environ.get("PAPER2_AI_FINAL_EVALUATION_AUTHORIZED") != "YES":
        raise PermissionError("final evaluation authorization flag mismatch")
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise PermissionError("final evaluation requires GitHub Actions")
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise PermissionError("final evaluation requires workflow_dispatch")
    if os.environ.get("GITHUB_REPOSITORY") != FROZEN_REPOSITORY:
        raise PermissionError("final evaluation repository mismatch")
    if os.environ.get("GITHUB_REF") != FROZEN_WORKFLOW_REF:
        raise PermissionError("final evaluation frozen ref mismatch")
    if os.environ.get("GITHUB_WORKFLOW_REF") != _expected_workflow_ref():
        raise PermissionError("final evaluation workflow ref/path mismatch")
    if os.environ.get("PAPER2_AI_FROZEN_EVALUATOR_SHA") != FROZEN_EVALUATOR_SHA:
        raise PermissionError("frozen evaluator SHA mismatch")

    github_sha = _full_sha(os.environ.get("GITHUB_SHA", ""), "GITHUB_SHA")
    workflow_sha = _full_sha(
        os.environ.get("GITHUB_WORKFLOW_SHA", ""), "GITHUB_WORKFLOW_SHA"
    )
    env_workflow_sha = _full_sha(
        os.environ.get("PAPER2_AI_FROZEN_WORKFLOW_SHA", ""),
        "PAPER2_AI_FROZEN_WORKFLOW_SHA",
    )
    if github_sha != workflow_sha or github_sha != env_workflow_sha:
        raise PermissionError("workflow execution SHA differs from workflow source SHA")

    run_id = _positive_int(os.environ.get("GITHUB_RUN_ID"), "GITHUB_RUN_ID")
    run_attempt = _positive_int(
        os.environ.get("GITHUB_RUN_ATTEMPT"), "GITHUB_RUN_ATTEMPT"
    )
    if run_attempt != 1:
        raise PermissionError(
            "GitHub rerun attempts are forbidden; use a new workflow_dispatch with resume_run_id"
        )

    workflow_file = Path(control_root) / FROZEN_WORKFLOW_PATH
    if not workflow_file.is_file():
        raise FileNotFoundError("audited workflow file is missing from control checkout")
    actual_blob = _git_blob_sha(workflow_file)
    if actual_blob != FROZEN_WORKFLOW_BLOB_SHA:
        raise PermissionError("workflow file differs from audited frozen content")

    return {
        "protocol": WORKFLOW_PROTOCOL,
        "repository": FROZEN_REPOSITORY,
        "frozen_ref": FROZEN_WORKFLOW_REF,
        "workflow_ref": _expected_workflow_ref(),
        "workflow_sha": github_sha,
        "workflow_blob_sha": actual_blob,
        "evaluator_sha": FROZEN_EVALUATOR_SHA,
        "registry_sha256": FROZEN_REGISTRY_SHA256,
        "current_run_id": run_id,
        "current_run_attempt": run_attempt,
    }


def _validate_static_manifest(manifest: dict, env: dict) -> None:
    expected = {
        "protocol": WORKFLOW_PROTOCOL,
        "repository": FROZEN_REPOSITORY,
        "frozen_ref": FROZEN_WORKFLOW_REF,
        "workflow_ref": _expected_workflow_ref(),
        "workflow_sha": env["workflow_sha"],
        "workflow_blob_sha": FROZEN_WORKFLOW_BLOB_SHA,
        "evaluator_sha": FROZEN_EVALUATOR_SHA,
        "registry_sha256": FROZEN_REGISTRY_SHA256,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"run manifest {key} mismatch")


def prepare_run(
    *,
    control_root: Path,
    output: Path,
    resume_run_id: int | None = None,
    prior_manifest: Path | None = None,
) -> dict:
    env = validate_environment(control_root)
    if Path(output).exists():
        raise FileExistsError("run contract output already exists")

    parent_sha256 = None
    if resume_run_id is None:
        if prior_manifest is not None:
            raise ValueError("prior_manifest is forbidden on a first run")
        origin_run_id = env["current_run_id"]
    else:
        resume_run_id = _positive_int(resume_run_id, "resume_run_id")
        if prior_manifest is None:
            raise ValueError("resume requires the prior run contract artifact")
        prior_path = Path(prior_manifest)
        if not prior_path.is_file():
            raise FileNotFoundError("prior run contract artifact is missing")
        prior_bytes = prior_path.read_bytes()
        prior = json.loads(prior_bytes)
        if not isinstance(prior, dict):
            raise ValueError("prior run contract must contain one JSON object")
        _validate_static_manifest(prior, env)
        if _positive_int(prior.get("current_run_id"), "prior current_run_id") != resume_run_id:
            raise ValueError("prior run contract does not belong to requested resume_run_id")
        if _positive_int(prior.get("current_run_attempt"), "prior current_run_attempt") != 1:
            raise ValueError("prior run contract came from a forbidden rerun attempt")
        if env["current_run_id"] == resume_run_id:
            raise ValueError("resume must use a new workflow_dispatch run id")
        origin_run_id = _positive_int(prior.get("origin_run_id"), "origin_run_id")
        parent_sha256 = hashlib.sha256(prior_bytes).hexdigest()

    manifest = {
        **{k: env[k] for k in (
            "protocol", "repository", "frozen_ref", "workflow_ref",
            "workflow_sha", "workflow_blob_sha", "evaluator_sha",
            "registry_sha256", "current_run_id", "current_run_attempt",
        )},
        "origin_run_id": origin_run_id,
        "resume_from_run_id": resume_run_id,
        "parent_manifest_sha256": parent_sha256,
    }
    _atomic_json(Path(output), manifest)
    return manifest


def validate_current_run(*, control_root: Path, manifest_path: Path) -> dict:
    env = validate_environment(control_root)
    manifest = _read_json(Path(manifest_path))
    _validate_static_manifest(manifest, env)
    if _positive_int(manifest.get("current_run_id"), "current_run_id") != env["current_run_id"]:
        raise ValueError("run contract current_run_id differs from this workflow run")
    if _positive_int(
        manifest.get("current_run_attempt"), "current_run_attempt"
    ) != env["current_run_attempt"]:
        raise ValueError("run contract current_run_attempt differs from this workflow run")
    origin = _positive_int(manifest.get("origin_run_id"), "origin_run_id")
    resume = manifest.get("resume_from_run_id")
    if resume is None:
        if origin != env["current_run_id"]:
            raise ValueError("first-run origin_run_id must equal current_run_id")
        if manifest.get("parent_manifest_sha256") is not None:
            raise ValueError("first run cannot have a parent manifest")
    else:
        _positive_int(resume, "resume_from_run_id")
        parent = str(manifest.get("parent_manifest_sha256") or "")
        if len(parent) != 64 or any(c not in "0123456789abcdef" for c in parent):
            raise ValueError("resume run must bind the prior manifest SHA-256")
    return manifest


def _expected_shard_contract(manifest: dict, shard_id: int):
    from paper2_model0.ai import evaluation_execution as ex

    if not 0 <= int(shard_id) < ex.SHARD_COUNT:
        raise ValueError("shard_id must be in frozen range 0..39")
    shard = ex.evaluation_shards()[int(shard_id)]
    expected = ex.build_execution_contract(
        shard=shard,
        source_commit_sha=FROZEN_EVALUATOR_SHA,
        workflow_commit_sha=manifest["workflow_sha"],
        origin_run_id=_positive_int(manifest["origin_run_id"], "origin_run_id"),
    )
    return ex, shard, expected


def validate_restored_shard(
    *, control_root: Path, manifest_path: Path, shard_dir: Path, shard_id: int
) -> dict:
    manifest = validate_current_run(
        control_root=Path(control_root), manifest_path=Path(manifest_path)
    )
    if manifest.get("resume_from_run_id") is None:
        raise ValueError("restored shard is allowed only for an explicit resume run")
    ex, shard, expected = _expected_shard_contract(manifest, int(shard_id))
    root = Path(shard_dir)
    if not root.is_dir():
        raise FileNotFoundError("requested prior shard artifact is missing")
    store = ex.EvaluationShardStore(root, shard)
    committed, history = store.load(expected)
    return {
        "shard_id": shard.shard_id,
        "committed_scenarios": committed,
        "history_entries": len(history),
        "complete": store.complete_path.exists(),
    }


def validate_collector_set(
    *, control_root: Path, manifest_path: Path, shard_parent: Path
) -> dict:
    manifest = validate_current_run(
        control_root=Path(control_root), manifest_path=Path(manifest_path)
    )

    from paper2_model0.ai import evaluation_execution as ex

    parent = Path(shard_parent)
    if not parent.is_dir():
        raise FileNotFoundError("collector shard parent is missing")
    expected_names = {f"shard-{i:03d}" for i in range(ex.SHARD_COUNT)}
    entries = list(parent.iterdir())
    actual_names = {path.name for path in entries}
    if actual_names != expected_names or any(not path.is_dir() for path in entries):
        raise ValueError("collector requires exactly the forty frozen shard artifacts")

    total_rows = 0
    for shard in ex.evaluation_shards():
        root = parent / f"shard-{shard.shard_id:03d}"
        expected = ex.build_execution_contract(
            shard=shard,
            source_commit_sha=FROZEN_EVALUATOR_SHA,
            workflow_commit_sha=manifest["workflow_sha"],
            origin_run_id=_positive_int(manifest["origin_run_id"], "origin_run_id"),
        )
        store = ex.EvaluationShardStore(root, shard)
        committed, history = store.load(expected)
        if committed != len(shard.scenario_indices):
            raise ValueError("collector refuses an incomplete shard")
        if not store.complete_path.is_file():
            raise ValueError("collector requires COMPLETE.json for every shard")
        complete = _read_json(store.complete_path)
        history_sha = hashlib.sha256(
            json.dumps(history, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if complete.get("contract") != expected:
            raise ValueError("collector completion contract mismatch")
        if complete.get("history_sha256") != history_sha:
            raise ValueError("collector completion history digest mismatch")
        rows = int(complete.get("rows", -1))
        if rows != len(shard.scenario_indices) * ex.COMBINATIONS_PER_SCENARIO:
            raise ValueError("collector completion row count mismatch")
        total_rows += rows
    if total_rows != ex.TOTAL_TRAJECTORIES:
        raise ValueError("collector total trajectory count mismatch")
    return {"shards": ex.SHARD_COUNT, "rows": total_rows}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="command", required=True)

    prepare = subs.add_parser("prepare-run")
    prepare.add_argument("--control-root", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--resume-run-id", type=int)
    prepare.add_argument("--prior-manifest", type=Path)

    current = subs.add_parser("validate-current-run")
    current.add_argument("--control-root", type=Path, required=True)
    current.add_argument("--manifest", type=Path, required=True)

    shard = subs.add_parser("validate-restored-shard")
    shard.add_argument("--control-root", type=Path, required=True)
    shard.add_argument("--manifest", type=Path, required=True)
    shard.add_argument("--shard-dir", type=Path, required=True)
    shard.add_argument("--shard-id", type=int, required=True)

    collector = subs.add_parser("validate-collector-set")
    collector.add_argument("--control-root", type=Path, required=True)
    collector.add_argument("--manifest", type=Path, required=True)
    collector.add_argument("--shard-parent", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "prepare-run":
        result = prepare_run(
            control_root=args.control_root,
            output=args.output,
            resume_run_id=args.resume_run_id,
            prior_manifest=args.prior_manifest,
        )
    elif args.command == "validate-current-run":
        result = validate_current_run(
            control_root=args.control_root, manifest_path=args.manifest
        )
    elif args.command == "validate-restored-shard":
        result = validate_restored_shard(
            control_root=args.control_root,
            manifest_path=args.manifest,
            shard_dir=args.shard_dir,
            shard_id=args.shard_id,
        )
    else:
        result = validate_collector_set(
            control_root=args.control_root,
            manifest_path=args.manifest,
            shard_parent=args.shard_parent,
        )
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
