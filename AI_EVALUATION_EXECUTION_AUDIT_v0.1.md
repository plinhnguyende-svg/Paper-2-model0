# Final evaluation execution/durability candidate v0.1

Status: IMPLEMENTATION FOR REVIEW. Held-out evaluation remains unconditionally
closed. This commit must not be treated as authorization to generate final
scientific outcomes.

## Gate already completed before this change

The real-archive loader preflight on PR #12 passed on run `35505094523`.
It loaded exactly 15 registered training artifacts on Ubuntu 24.04 / Python
3.12.14 under the locked runtime, verified the registry/checkpoint/manifest
chain, and reported `heldout_scenarios_generated=0`. The audit artifact is
`evaluation-loader-audit-a850bc0dab60acd61becaafdf6483711f19c15d0`.

## Execution contract added

The candidate execution layer now predefines a static 40-shard partition:
5 evaluation scenarios per shard, 200 scenarios total, with all 18 frozen
regime/decision-policy combinations evaluated inside each scenario. Therefore
the final panel remains exactly 3,600 trajectories; sharding is operational
only and does not change the scientific design.

Each shard carries an immutable contract binding:
- exact source commit SHA and workflow commit SHA;
- origin GitHub run ID;
- frozen checkpoint-registry SHA and freeze commit;
- deterministic 200-seed evaluation schedule hash;
- static shard-registry hash;
- exact runtime fingerprint;
- shard ID and exact scenario interval.

A scenario is locally committed only after its 18-row JSONL payload is fsynced
and then referenced by an atomically replaced latest pointer. Restore verifies
the complete immutable history and every file digest. Crucially, ambiguous
temporary files or unreferenced scenario output cause a fail-closed error.
They are not deleted and the scenario is not silently rerun.

Shard completion is impossible before all five scenario records exist and
validate. The collector requires all 40 distinct shard directories, verifies
contracts against independently supplied frozen expectations, rejects missing
or duplicate scenarios, and re-runs the final-panel validator before writing a
single 3,600-row panel.

## What remains intentionally blocked

`run_evaluation_shard()` calls the existing unconditional
`require_evaluation_freeze()` before checkpoint access, output creation, or
held-out scenario generation. The new PR-only workflow runs contract tests and
a synthetic interruption/recovery exercise only. It has no `workflow_dispatch`
trigger and cannot launch final evaluation.

Remote GitHub artifact durability is not equated with local fsync. The eventual
frozen dispatch workflow must reserve time for upload, upload shard evidence
with `if: always()`, bind restored artifacts to the exact prior run/attempt,
and fail closed when durable prior evidence is absent or ambiguous. A hard
runner loss before remote upload remains explicitly unrecoverable without a
reviewed manual decision; this candidate does not silently infer that the shard
never ran.

## Next freeze gate

Before any held-out run:
1. Review this execution/store contract and synthetic interruption test.
2. Add the final dispatch workflow on a dedicated freeze commit, pinning the
   exact evaluator source/ref, runtime, thread settings, static 40-shard matrix,
   artifact names, first-run/resume authorization and collector contract.
3. Test that workflow without held-out access, including partial failure and
   resume-artifact provenance.
4. Only then freeze the evaluator/workflow and separately authorize the first
   3,600-trajectory run.
