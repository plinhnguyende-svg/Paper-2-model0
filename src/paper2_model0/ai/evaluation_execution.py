"""Crash-safe execution layer for the frozen final-evaluation candidate.

This module does not authorize held-out evaluation. The scientific entry point
calls evaluation.require_evaluation_freeze() before archive access, output
creation, or scenario generation. Until a later freeze commit replaces that
unconditional gate with exact reviewed authorization, held-out execution stays
closed.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

import pandas as pd
import torch

from . import evaluation as ev
from .training_protocol import INFORMATION_REGIMES, TRAINING_SEEDS, runtime_fingerprint


EXECUTION_PROTOCOL_VERSION = "ai-final-evaluation-execution-v0.1"
SCENARIO_COUNT = 200
COMBINATIONS_PER_SCENARIO = 18
SCENARIOS_PER_SHARD = 5
SHARD_COUNT = SCENARIO_COUNT // SCENARIOS_PER_SHARD
TOTAL_TRAJECTORIES = SCENARIO_COUNT * COMBINATIONS_PER_SCENARIO


@dataclass(frozen=True)
class EvaluationShard:
    shard_id: int
    start_scenario: int
    stop_scenario: int

    @property
    def scenario_indices(self) -> tuple[int, ...]:
        return tuple(range(self.start_scenario, self.stop_scenario))


def evaluation_shards() -> tuple[EvaluationShard, ...]:
    shards = tuple(
        EvaluationShard(i, i * SCENARIOS_PER_SHARD, (i + 1) * SCENARIOS_PER_SHARD)
        for i in range(SHARD_COUNT)
    )
    indices = [i for shard in shards for i in shard.scenario_indices]
    if indices != list(range(SCENARIO_COUNT)):
        raise AssertionError("static evaluation shard registry must cover 0..199 exactly once")
    return shards


def shard_registry_sha256() -> str:
    payload = [
        {
            "shard_id": s.shard_id,
            "start_scenario": s.start_scenario,
            "stop_scenario": s.stop_scenario,
        }
        for s in evaluation_shards()
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def evaluation_schedule_sha256() -> str:
    return hashlib.sha256(
        json.dumps(ev.evaluation_seed_schedule(), separators=(",", ":")).encode()
    ).hexdigest()


def _full_sha(value: str, label: str) -> str:
    value = str(value).strip().lower()
    if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{label} must be a full lowercase git SHA")
    return value


def build_execution_contract(
    *,
    shard: EvaluationShard,
    source_commit_sha: str,
    workflow_commit_sha: str,
    origin_run_id: int,
) -> dict:
    if shard not in evaluation_shards():
        raise ValueError("shard is not in the frozen static registry")
    if int(origin_run_id) <= 0:
        raise ValueError("origin_run_id must be positive")
    return {
        "protocol_version": EXECUTION_PROTOCOL_VERSION,
        "source_commit_sha": _full_sha(source_commit_sha, "source_commit_sha"),
        "workflow_commit_sha": _full_sha(workflow_commit_sha, "workflow_commit_sha"),
        "origin_run_id": int(origin_run_id),
        "registry_sha256": ev.REGISTRY_SHA256,
        "registry_freeze_commit": ev.REGISTRY_FREEZE_COMMIT,
        "evaluation_schedule_sha256": evaluation_schedule_sha256(),
        "shard_registry_sha256": shard_registry_sha256(),
        "shard_id": shard.shard_id,
        "start_scenario": shard.start_scenario,
        "stop_scenario": shard.stop_scenario,
        "runtime": runtime_fingerprint(),
    }


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)
    try:
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def _atomic_json(path: Path, value: dict) -> None:
    _atomic_bytes(
        path,
        (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode(),
    )


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _rows_bytes(rows: list[dict]) -> bytes:
    return "".join(
        json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in rows
    ).encode()


def _expected_keys() -> set[tuple[str, str, int | None]]:
    expected: set[tuple[str, str, int | None]] = set()
    for regime in INFORMATION_REGIMES:
        expected.add((regime, "RuleBased", None))
        expected.update((regime, "AI", seed) for seed in TRAINING_SEEDS)
    if len(expected) != COMBINATIONS_PER_SCENARIO:
        raise AssertionError("evaluation combination registry drift")
    return expected


def validate_scenario_rows(rows: list[dict], scenario_index: int, contract: dict) -> None:
    if len(rows) != COMBINATIONS_PER_SCENARIO:
        raise ValueError("each evaluation scenario must contain exactly 18 rows")
    if {int(row.get("scenario_index", -1)) for row in rows} != {scenario_index}:
        raise ValueError("scenario row index mismatch")
    scenario_ids = {str(row.get("scenario_id", "")) for row in rows}
    scenario_seeds = {str(row.get("evaluation_scenario_seed", "")) for row in rows}
    if len(scenario_ids) != 1 or "" in scenario_ids:
        raise ValueError("scenario_id must be common and non-empty")
    if len(scenario_seeds) != 1 or "" in scenario_seeds:
        raise ValueError("evaluation scenario seed must be common and non-empty")
    keys = {
        (
            str(row.get("regime")),
            str(row.get("decision_architecture")),
            None if row.get("training_seed") is None else int(row["training_seed"]),
        )
        for row in rows
    }
    if keys != _expected_keys():
        raise ValueError("scenario rows do not contain the exact 18 frozen combinations")
    for row in rows:
        if row.get("source_sha") != contract["source_commit_sha"]:
            raise ValueError("row source SHA differs from execution contract")
        if row.get("registry_sha256") != ev.REGISTRY_SHA256:
            raise ValueError("row registry SHA differs from frozen registry")
        for metric in ev.PRIMARY + ev.SECONDARY:
            value = row.get(metric)
            if value is None:
                raise ValueError("undefined outcome is retained but cannot enter final panel")
            if not pd.notna(value):
                raise ValueError("non-finite evaluation outcome")


class EvaluationShardStore:
    """Fail-closed local shard store.

    A scenario becomes committed only after its immutable JSONL file is fsynced
    and the latest pointer is atomically replaced. Unlike the training store,
    ambiguous orphan or temporary files are never silently deleted: restore
    fails closed so a human can audit whether a held-out trajectory might have
    run without durable provenance.
    """

    def __init__(self, root: str | Path, shard: EvaluationShard):
        self.root = Path(root)
        self.shard = shard
        self.state_dir = self.root / "state"
        self.contract_path = self.state_dir / "contract.json"
        self.latest_path = self.state_dir / "latest.json"
        self.complete_path = self.root / "COMPLETE.json"

    def scenario_path(self, scenario_index: int) -> Path:
        return self.root / "rows" / f"scenario_{scenario_index:03d}.jsonl"

    def initialize(self, contract: dict) -> None:
        if self.root.exists():
            raise FileExistsError("first-run shard output already exists")
        if int(contract["shard_id"]) != self.shard.shard_id:
            raise ValueError("contract shard mismatch")
        self.state_dir.mkdir(parents=True, exist_ok=False)
        _atomic_json(self.contract_path, contract)
        _atomic_json(self.latest_path, {"committed_scenarios": 0, "history": []})

    def _validate_no_ambiguous_files(self, history: list[dict]) -> None:
        referenced = {str(item["file"]) for item in history}
        for directory in (self.state_dir, self.root / "rows"):
            if not directory.exists():
                continue
            for path in directory.iterdir():
                if path.name.endswith(".tmp"):
                    raise RuntimeError("ambiguous temporary evaluation state; resume is forbidden")
        if (self.root / "rows").exists():
            for path in (self.root / "rows").glob("scenario_*.jsonl"):
                relative = str(path.relative_to(self.root))
                if relative not in referenced:
                    raise RuntimeError("uncommitted scenario output exists; resume is forbidden")

    def load(self, expected_contract: dict) -> tuple[int, list[dict]]:
        if not self.contract_path.exists() or not self.latest_path.exists():
            raise FileNotFoundError("durable shard state is incomplete; resume is forbidden")
        contract = _json(self.contract_path)
        if contract != expected_contract:
            raise ValueError("restored execution contract differs from frozen expectation")
        latest = _json(self.latest_path)
        if set(latest) != {"committed_scenarios", "history"}:
            raise ValueError("invalid shard latest pointer")
        history = latest["history"]
        committed = int(latest["committed_scenarios"])
        if committed != len(history) or not 0 <= committed <= len(self.shard.scenario_indices):
            raise ValueError("invalid committed scenario count")
        self._validate_no_ambiguous_files(history)
        for position, item in enumerate(history):
            expected_index = self.shard.scenario_indices[position]
            if int(item.get("scenario_index", -1)) != expected_index:
                raise ValueError("committed shard history must be contiguous")
            path = self.root / str(item["file"])
            if not path.exists():
                raise FileNotFoundError("committed scenario file is missing")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != item.get("sha256"):
                raise ValueError("committed scenario digest mismatch")
        return committed, history

    def commit_scenario(self, rows: list[dict], contract: dict) -> None:
        committed, history = self.load(contract)
        if committed >= len(self.shard.scenario_indices):
            raise ValueError("shard is already complete")
        scenario_index = self.shard.scenario_indices[committed]
        validate_scenario_rows(rows, scenario_index, contract)
        path = self.scenario_path(scenario_index)
        if path.exists():
            raise FileExistsError("scenario output already exists; replay is forbidden")
        data = _rows_bytes(rows)
        _atomic_bytes(path, data)
        item = {
            "scenario_index": scenario_index,
            "file": str(path.relative_to(self.root)),
            "sha256": hashlib.sha256(data).hexdigest(),
            "rows": len(rows),
        }
        _atomic_json(
            self.latest_path,
            {"committed_scenarios": committed + 1, "history": [*history, item]},
        )

    def finalize(self, contract: dict) -> dict:
        committed, history = self.load(contract)
        if committed != len(self.shard.scenario_indices):
            raise ValueError("cannot finalize an incomplete evaluation shard")
        if self.complete_path.exists():
            raise FileExistsError("shard completion record already exists")
        row_count = sum(int(item["rows"]) for item in history)
        if row_count != len(self.shard.scenario_indices) * COMBINATIONS_PER_SCENARIO:
            raise AssertionError("shard row count mismatch")
        completion = {
            "contract": contract,
            "committed_scenarios": committed,
            "rows": row_count,
            "history_sha256": hashlib.sha256(
                json.dumps(history, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }
        _atomic_json(self.complete_path, completion)
        return completion


def _load_policies(archive_dir: Path):
    policies = {}
    training_ids = set()
    for regime in INFORMATION_REGIMES:
        for seed in TRAINING_SEEDS:
            policy, entry, manifest = ev.load_registered_policy(
                archive_dir / f"ai-training-{regime}-seed-{seed}.zip", regime, seed
            )
            policies[regime, seed] = (policy, entry)
            training_ids.update(record["scenario_id"] for record in manifest["episodes"])
    return policies, training_ids


def run_evaluation_shard(
    *,
    archive_dir: Path,
    output_dir: Path,
    shard_id: int,
    source_commit_sha: str,
    workflow_commit_sha: str,
    origin_run_id: int,
    resume: bool,
) -> dict:
    # Blocking scientific gate: currently unconditional and intentionally first.
    ev.require_evaluation_freeze()
    shard = evaluation_shards()[int(shard_id)]
    contract = build_execution_contract(
        shard=shard,
        source_commit_sha=source_commit_sha,
        workflow_commit_sha=workflow_commit_sha,
        origin_run_id=origin_run_id,
    )
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    policies, training_ids = _load_policies(archive_dir)
    store = EvaluationShardStore(output_dir, shard)
    if resume:
        committed, _ = store.load(contract)
    else:
        store.initialize(contract)
        committed = 0
    config = ev.SimulationConfig()
    schedule = ev.evaluation_seed_schedule()
    for scenario_index in shard.scenario_indices[committed:]:
        scenario = ev.generate_scenario(config, schedule[scenario_index])
        if scenario.scenario_id in training_ids:
            raise ValueError("held-out scenario overlaps training")
        rows = []
        for regime in INFORMATION_REGIMES:
            for training_seed in (None, *TRAINING_SEEDS):
                policy, entry = (
                    (None, None)
                    if training_seed is None
                    else policies[regime, training_seed]
                )
                rows.append(
                    {
                        "scenario_index": scenario_index,
                        "scenario_id": scenario.scenario_id,
                        "evaluation_scenario_seed": str(schedule[scenario_index]),
                        "regime": regime,
                        "decision_architecture": "RuleBased" if policy is None else "AI",
                        "training_seed": training_seed,
                        "checkpoint_sha256": (
                            None if entry is None else entry["final_checkpoint_sha256"]
                        ),
                        "source_sha": contract["source_commit_sha"],
                        "registry_sha256": ev.REGISTRY_SHA256,
                        **ev._evaluate_one(config, scenario, regime, policy),
                    }
                )
        store.commit_scenario(rows, contract)
    return store.finalize(contract)


def collect_evaluation_shards(
    shard_dirs: Iterable[Path],
    *,
    output_file: Path,
    source_commit_sha: str,
    workflow_commit_sha: str,
    origin_run_id: int,
) -> dict:
    dirs = {path.name: Path(path) for path in shard_dirs}
    if len(dirs) != SHARD_COUNT:
        raise ValueError("collector requires exactly 40 distinct shard directories")
    rows: list[dict] = []
    scenario_seen: set[int] = set()
    for shard in evaluation_shards():
        root = next(
            (path for path in dirs.values() if path.name == f"shard-{shard.shard_id:03d}"),
            None,
        )
        if root is None:
            raise ValueError(f"missing shard-{shard.shard_id:03d}")
        expected = build_execution_contract(
            shard=shard,
            source_commit_sha=source_commit_sha,
            workflow_commit_sha=workflow_commit_sha,
            origin_run_id=origin_run_id,
        )
        store = EvaluationShardStore(root, shard)
        committed, history = store.load(expected)
        if committed != len(shard.scenario_indices) or not store.complete_path.exists():
            raise ValueError("collector refuses incomplete shard evidence")
        complete = _json(store.complete_path)
        if complete.get("contract") != expected:
            raise ValueError("completion contract mismatch")
        for item in history:
            scenario_index = int(item["scenario_index"])
            if scenario_index in scenario_seen:
                raise ValueError("duplicate scenario across shard evidence")
            scenario_seen.add(scenario_index)
            path = root / item["file"]
            for line in path.read_text(encoding="utf-8").splitlines():
                rows.append(json.loads(line))
    if scenario_seen != set(range(SCENARIO_COUNT)) or len(rows) != TOTAL_TRAJECTORIES:
        raise ValueError("final panel must contain 200 scenarios and exactly 3600 rows")
    frame = pd.DataFrame(rows).sort_values(
        ["scenario_index", "regime", "decision_architecture", "training_seed"],
        na_position="first",
    )
    # Independent final-panel validation uses frozen expectations, not shard claims.
    for metric in ev.PRIMARY:
        from .evaluation_analysis import panel_arrays
        panel_arrays(frame, metric)
    data = "".join(
        json.dumps(row, sort_keys=True, allow_nan=False) + "\n"
        for row in frame.to_dict(orient="records")
    ).encode()
    _atomic_bytes(output_file, data)
    return {
        "rows": len(frame),
        "scenarios": len(scenario_seen),
        "panel_sha256": hashlib.sha256(data).hexdigest(),
        "source_commit_sha": _full_sha(source_commit_sha, "source_commit_sha"),
        "workflow_commit_sha": _full_sha(workflow_commit_sha, "workflow_commit_sha"),
        "origin_run_id": int(origin_run_id),
    }
