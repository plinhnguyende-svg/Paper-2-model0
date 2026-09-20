"""Frozen final-evaluation shard CLI; no scientific inputs are exposed."""
import argparse
from pathlib import Path

from paper2_model0.ai import evaluation as ev
from paper2_model0.ai.evaluation_execution import run_evaluation_shard


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--shard-id", type=int, required=True)
    parser.add_argument("--origin-run-id", type=int, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    auth = ev.require_evaluation_freeze()
    result = run_evaluation_shard(
        archive_dir=args.archive_dir,
        output_dir=args.output_dir,
        shard_id=args.shard_id,
        source_commit_sha=auth["evaluator_sha"],
        workflow_commit_sha=auth["workflow_sha"],
        origin_run_id=args.origin_run_id,
        resume=args.resume,
    )
    print({
        "shard_id": args.shard_id,
        "rows": result["rows"],
        "committed_scenarios": result["committed_scenarios"],
    })
