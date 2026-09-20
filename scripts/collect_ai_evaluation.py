"""Frozen final-evaluation collector CLI."""
import argparse
from pathlib import Path

from paper2_model0.ai import evaluation as ev
from paper2_model0.ai.evaluation_execution import collect_evaluation_shards, evaluation_shards


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard-parent", type=Path, required=True)
    parser.add_argument("--output-file", type=Path, required=True)
    parser.add_argument("--origin-run-id", type=int, required=True)
    args = parser.parse_args()
    auth = ev.require_evaluation_freeze()
    result = collect_evaluation_shards(
        [args.shard_parent / f"shard-{s.shard_id:03d}" for s in evaluation_shards()],
        output_file=args.output_file,
        source_commit_sha=auth["evaluator_sha"],
        workflow_commit_sha=auth["workflow_sha"],
        origin_run_id=args.origin_run_id,
    )
    print(result)
